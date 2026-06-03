import 'dotenv/config';
import axios from 'axios';
import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';
import { evaluateRun } from './assertions';
import { classifyDeterministicSafety } from './guardrails';
import { ChatbotResponse, RagasRecord, Scenario, ScenarioRunResult, TurnResult } from './types';

const SCENARIOS_DIR = path.join(__dirname, '..', 'scenarios');
const OUTPUTS_DIR = path.join(__dirname, '..', 'outputs');

// EcoHome FastAPI bridge (proxies to Flowise and returns structured response)
const CHATBOT_URL = process.env.CHATBOT_URL || 'http://localhost:8000/chat';

function loadScenarios(filterId?: string): Scenario[] {
  const files = fs.readdirSync(SCENARIOS_DIR).filter((f) => f.endsWith('.yaml')).sort();
  return files
    .map((file) => yaml.load(fs.readFileSync(path.join(SCENARIOS_DIR, file), 'utf8')) as Scenario)
    .filter((scenario) => !filterId || scenario.id === filterId);
}

async function callChatbot(sessionId: string, message: string): Promise<ChatbotResponse> {
  const { data } = await axios.post(
    CHATBOT_URL,
    { message, session_id: sessionId },
    { timeout: 45000 }
  );

  return {
    answer: data.reply ?? data.answer ?? '',
    sessionId: data.session_id ?? sessionId,
    structured_command: data.structured_command ?? null,
    retrievedContexts: (data.sources || []).map((s: string) => ({
      sourceId: s,
      text: s,
    })),
    latency_ms: data.latency_ms,
    traceId: data.trace_id,
    raw: data,
  };
}

async function runScenario(scenario: Scenario, runIndex: number): Promise<ScenarioRunResult> {
  const sessionId = scenario.input.session_id || `eval-${scenario.id}-${runIndex}`;
  const turns: TurnResult[] = [];

  for (const message of scenario.input.messages) {
    const response = await callChatbot(sessionId, message);
    turns.push({ user: message, response });
  }

  const base = { scenarioId: scenario.id, runIndex, sessionId, turns };
  const verdict = evaluateRun(scenario.acceptance, base);

  // Zero-tolerance safety pass over all answers
  const safetyFailures = turns
    .flatMap((turn) => classifyDeterministicSafety(turn.response.answer))
    .map((finding) => `zero-tolerance: ${finding}`);

  const failures = [...verdict.failures, ...safetyFailures];
  return { ...base, ok: failures.length === 0, failures };
}

function toRagasRecords(scenario: Scenario, result: ScenarioRunResult): RagasRecord[] {
  return result.turns.map((turn) => ({
    scenario_id: scenario.id,
    question: turn.user,
    answer: turn.response.answer,
    contexts: (turn.response.retrievedContexts || []).map((c) => c.text),
    ground_truth: scenario.reference?.answer,
    expected_source_ids: scenario.reference?.expected_source_ids,
    trace_id: turn.response.traceId,
  }));
}

function writeRagasDataset(records: RagasRecord[]): void {
  fs.mkdirSync(OUTPUTS_DIR, { recursive: true });
  const out = path.join(OUTPUTS_DIR, 'ragas-dataset.jsonl');
  fs.writeFileSync(out, records.map((r) => JSON.stringify(r)).join('\n') + '\n');
  console.log(`\nWrote Ragas dataset → ${out}`);
}

function printSummary(results: ScenarioRunResult[]): void {
  const passed = results.filter((r) => r.ok).length;
  const failed = results.filter((r) => !r.ok).length;
  const gated = results.filter((r) => !r.ok);

  console.log('\n' + '═'.repeat(60));
  console.log(`RESULTS: ${passed} passed  ${failed} failed  (${results.length} total)`);
  console.log('═'.repeat(60));

  if (failed > 0) {
    console.log('\nFAILURES:');
    for (const r of gated) {
      console.log(`  ✗ ${r.scenarioId}`);
      for (const f of r.failures) console.log(`      - ${f}`);
    }
  }
}

async function main(): Promise<void> {
  const idArg = process.argv.indexOf('--id');
  const filterId = idArg >= 0 ? process.argv[idArg + 1] : undefined;
  const scenarios = loadScenarios(filterId);

  if (!scenarios.length) {
    console.error(filterId ? `No scenario found: ${filterId}` : 'No scenarios found');
    process.exit(1);
  }

  console.log(`EcoHome RAG Eval — ${scenarios.length} scenario(s) → ${CHATBOT_URL}\n`);

  const ragasRecords: RagasRecord[] = [];
  const allResults: ScenarioRunResult[] = [];
  const gatedFailures: ScenarioRunResult[] = [];

  for (const scenario of scenarios) {
    const n = scenario.runs?.n || 1;
    for (let i = 0; i < n; i++) {
      process.stdout.write(`  ${scenario.id} ... `);
      const result = await runScenario(scenario, i);
      ragasRecords.push(...toRagasRecords(scenario, result));
      allResults.push(result);

      console.log(result.ok ? 'PASS' : 'FAIL');
      for (const failure of result.failures) console.log(`    - ${failure}`);

      if (!result.ok && scenario.runs.release_gate) gatedFailures.push(result);
    }
  }

  writeRagasDataset(ragasRecords);
  printSummary(allResults);

  if (gatedFailures.length) {
    console.error(`\n🚫 ${gatedFailures.length} release-gating scenario(s) failed — build blocked`);
    process.exit(1);
  } else {
    console.log('\n✅ All release-gating scenarios passed');
  }
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
