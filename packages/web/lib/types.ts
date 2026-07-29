export type RunStatus = "queued" | "analyze" | "benchmark" | "done" | "completed" | "failed";
export type TargetMode = "target" | "provisioned";
export type Backend = "llamacpp" | "vllm";
export type Arch = "x86_64" | "aarch64";

export interface RunCreateInput {
  workload_name: string;
  model_ref: string;
  source_path?: string;
  target_mode?: TargetMode;
  sla_p95_latency_ms: number;
  sla_accuracy_floor: number;
  cost_ceiling_usd?: number;
  search_budget_trials?: number;
  target_base_url?: string;
  target_instance_type?: string;
  target_arch?: Arch;
  target_price_per_hour?: number;
}

export interface Run {
  id: string;
  workload_id: string;
  status: RunStatus;
  stage: string | null;
  target_mode: TargetMode;
  sla_p95_latency_ms: number;
  sla_accuracy_floor: number;
  cost_ceiling_usd: number | null;
  search_budget_trials: number;
  selected_backend: Backend | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Trial {
  id: string;
  trial_number: number;
  backend: Backend;
  quant: string;
  threads: number;
  core_pinning: boolean;
  batch_size: number;
  kv_cache_precision: string;
  context_length: number;
  tokens_per_second: number;
  p95_latency_ms: number;
  cost_per_1m_tokens: number;
  accuracy_score: number;
  feasible: boolean;
  created_at: string;
}

export interface ResultRow {
  id: string;
  kind: string;
  result_json: BenchmarkResult;
  created_at: string;
}

export interface RunDetail extends Run {
  trials: Trial[];
  results: ResultRow[];
}

export interface BenchmarkResult {
  schema_version: string;
  run_id: string;
  timestamp: string;
  commit_sha: string;
  image_digest?: string;
  model: string;
  model_hash: string;
  backend: Backend;
  quant: string;
  instance_type: string;
  arch: Arch;
  price_per_hour: number;
  threads: number;
  core_pinning?: boolean;
  batch_size?: number;
  kv_cache_precision?: string;
  context_length?: number;
  concurrency: number;
  throughput: { tokens_per_second: number; requests_per_second: number };
  latency_ms: { ttft_p50: number; inter_token_p50?: number; p50: number; p95: number; p99: number };
  cost_per_1m_tokens: number;
  accuracy_score: number;
  baseline_ref?: string;
  notes?: string;
}

export interface RunEvent {
  stage: string | null;
  status: string;
  [key: string]: unknown;
}
