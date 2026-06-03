export interface Scenario {
  id: string;
  intent: string;
  description?: string;
  input: {
    session_id?: string;
    messages: string[];
  };
  reference?: {
    answer?: string;
    expected_source_ids?: string[];
  };
  acceptance: Acceptance;
  runs: {
    n: number;
    release_gate: boolean;
  };
}

export interface Acceptance {
  answer_must_refuse?: boolean;
  answer_must_mention_any?: string[];
  answer_must_not_mention?: string[];
  structured_command?: {
    must_trigger?: string;       // e.g. "[BOOK_CONSULTATION]"
    must_not_trigger?: string;
  };
  retrieval?: {
    min_contexts?: number;
    expected_source_ids?: string[];
  };
  ragas_thresholds?: {
    faithfulness?: number;
    answer_relevancy?: number;
    context_precision?: number;
    context_recall?: number;
  };
}

export interface RetrievedContext {
  sourceId?: string;
  text: string;
  score?: number;
}

export interface ChatbotResponse {
  answer: string;
  sessionId?: string;
  structured_command?: string | null;
  retrievedContexts?: RetrievedContext[];
  latency_ms?: number;
  traceId?: string;
  raw?: unknown;
}

export interface TurnResult {
  user: string;
  response: ChatbotResponse;
}

export interface ScenarioRunResult {
  scenarioId: string;
  runIndex: number;
  sessionId: string;
  ok: boolean;
  failures: string[];
  turns: TurnResult[];
}

export interface RagasRecord {
  scenario_id: string;
  question: string;
  answer: string;
  contexts: string[];
  ground_truth?: string;
  expected_source_ids?: string[];
  trace_id?: string;
}
