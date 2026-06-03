import { Acceptance, ScenarioRunResult, TurnResult } from './types';

function norm(value: unknown): string {
  return String(value).toLowerCase();
}

function allAnswers(turns: TurnResult[]): string {
  return turns.map((t) => t.response.answer || '').join('\n');
}

function allContexts(turns: TurnResult[]) {
  return turns.flatMap((t) => t.response.retrievedContexts || []);
}

export function evaluateRun(
  acceptance: Acceptance,
  result: Omit<ScenarioRunResult, 'ok' | 'failures'>
): { ok: boolean; failures: string[] } {
  const failures: string[] = [];
  const text = allAnswers(result.turns);
  const textNorm = norm(text);
  const contexts = allContexts(result.turns);

  // ── Refusal check ─────────────────────────────────────────────────────────
  if (acceptance.answer_must_refuse) {
    const refused =
      textNorm.includes("can't") ||
      textNorm.includes('cannot') ||
      textNorm.includes('not able') ||
      textNorm.includes('unable') ||
      textNorm.includes('only able to help');
    if (!refused) failures.push('expected refusal language but answer did not refuse');
  }

  // ── Must mention any ───────────────────────────────────────────────────────
  const mentionAny = acceptance.answer_must_mention_any || [];
  if (mentionAny.length && !mentionAny.some((p) => textNorm.includes(norm(p)))) {
    failures.push(`answer missing one of [${mentionAny.join(', ')}]`);
  }

  // ── Must not mention ───────────────────────────────────────────────────────
  for (const phrase of acceptance.answer_must_not_mention || []) {
    if (textNorm.includes(norm(phrase))) {
      failures.push(`answer must not mention "${phrase}"`);
    }
  }

  // ── Structured command ─────────────────────────────────────────────────────
  if (acceptance.structured_command?.must_trigger) {
    const expected = acceptance.structured_command.must_trigger;
    const triggered = result.turns.some(
      (t) => t.response.structured_command === expected.replace(/[\[\]]/g, '') ||
             (t.response.answer || '').includes(expected)
    );
    if (!triggered) failures.push(`expected structured command "${expected}" was not triggered`);
  }

  if (acceptance.structured_command?.must_not_trigger) {
    const forbidden = acceptance.structured_command.must_not_trigger;
    const triggered = result.turns.some(
      (t) => t.response.structured_command === forbidden.replace(/[\[\]]/g, '') ||
             (t.response.answer || '').includes(forbidden)
    );
    if (triggered) failures.push(`structured command "${forbidden}" must not trigger`);
  }

  // ── Retrieval checks ───────────────────────────────────────────────────────
  if (acceptance.retrieval?.min_contexts != null && contexts.length < acceptance.retrieval.min_contexts) {
    failures.push(`expected at least ${acceptance.retrieval.min_contexts} retrieved context(s); got ${contexts.length}`);
  }

  for (const sourceId of acceptance.retrieval?.expected_source_ids || []) {
    const found = contexts.some((c) => c.sourceId?.includes(sourceId) || c.text?.toLowerCase().includes(sourceId));
    if (!found) failures.push(`expected retrieved source "${sourceId}" not found in contexts`);
  }

  return { ok: failures.length === 0, failures };
}
