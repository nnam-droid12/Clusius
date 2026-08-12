"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Nav } from "@/components/Nav";
import { useCreateRun } from "@/lib/hooks";
import type { RunCreateInput } from "@/lib/types";

const initialState: RunCreateInput = {
  workload_name: "showcase-agent",
  model_ref: "qwen2.5-7b-instruct",
  source_path: "",
  target_mode: "target",
  sla_p95_latency_ms: 2000,
  sla_accuracy_floor: 0.9,
  search_budget_trials: 20,
  concurrency: 2,
  target_base_url: "",
};

export default function NewRunPage() {
  const router = useRouter();
  const [form, setForm] = useState<RunCreateInput>(initialState);
  const createRun = useCreateRun();

  function update<K extends keyof RunCreateInput>(key: K, value: RunCreateInput[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: RunCreateInput = {
      ...form,
      source_path: form.source_path || undefined,
      target_base_url: form.target_base_url || undefined,
    };
    const run = await createRun.mutateAsync(payload);
    router.push(`/runs/${run.id}`);
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-2xl px-6 py-12">
        <h1 className="text-2xl font-semibold tracking-tight">Launch a run</h1>
        <p className="mt-2 text-sm text-secondary">
          Target mode drives an existing C4A / x86 pair over SSH — no cloud credentials required.
          Leave the target endpoint blank to run only the (infra-free) analyze stage.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <Field label="Workload name">
            <input
              required
              value={form.workload_name}
              onChange={(e) => update("workload_name", e.target.value)}
              className="input"
            />
          </Field>

          <Field label="Model reference">
            <input
              required
              value={form.model_ref}
              onChange={(e) => update("model_ref", e.target.value)}
              className="input"
            />
          </Field>

          <Field
            label="Workload source path (optional)"
            hint="A local directory containing the workload's Dockerfile(s) for the analyze stage."
          >
            <input
              value={form.source_path}
              onChange={(e) => update("source_path", e.target.value)}
              className="input"
              placeholder="/path/to/workload"
            />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="p95 latency SLA (ms)">
              <input
                type="number"
                required
                value={form.sla_p95_latency_ms}
                onChange={(e) => update("sla_p95_latency_ms", Number(e.target.value))}
                className="input"
              />
            </Field>
            <Field label="Accuracy floor (0–1)">
              <input
                type="number"
                step="0.01"
                min={0}
                max={1}
                required
                value={form.sla_accuracy_floor}
                onChange={(e) => update("sla_accuracy_floor", Number(e.target.value))}
                className="input"
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Search budget (trials)">
              <input
                type="number"
                required
                value={form.search_budget_trials}
                onChange={(e) => update("search_budget_trials", Number(e.target.value))}
                className="input"
              />
            </Field>
            <Field
              label="Concurrency"
              hint="Low favors llama.cpp+KleidiAI; high favors vLLM's continuous batching."
            >
              <input
                type="number"
                min={1}
                required
                value={form.concurrency}
                onChange={(e) => update("concurrency", Number(e.target.value))}
                className="input"
              />
            </Field>
          </div>

          <Field
            label="Target endpoint (optional)"
            hint="An OpenAI-compatible base URL to benchmark for real as part of this run."
          >
            <input
              value={form.target_base_url}
              onChange={(e) => update("target_base_url", e.target.value)}
              className="input"
              placeholder="http://localhost:8090/v1"
            />
          </Field>

          {createRun.isError && (
            <p className="text-sm text-critical">{(createRun.error as Error).message}</p>
          )}

          <button
            type="submit"
            disabled={createRun.isPending}
            className="rounded-md bg-series-1 px-5 py-3 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {createRun.isPending ? "Launching…" : "Launch run"}
          </button>
        </form>
      </div>
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium">{label}</span>
      {hint && <span className="mt-0.5 block text-xs text-muted">{hint}</span>}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}
