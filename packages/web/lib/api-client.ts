import type { Run, RunCreateInput, RunDetail } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${response.status}): ${body}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  createRun: (input: RunCreateInput) =>
    request<Run>("/runs", { method: "POST", body: JSON.stringify(input) }),
  listRuns: () => request<Run[]>("/runs"),
  getRun: (id: string) => request<RunDetail>(`/runs/${id}`),
  getRunResult: (id: string) => request<Record<string, unknown>>(`/runs/${id}/result.json`),
  getRunReport: (id: string) => request<{ content: string; created_at: string }>(`/runs/${id}/report`),
  listResults: () => request<Run[]>("/results"),
  eventsUrl: (id: string) => `${API_URL}/runs/${id}/events`,
};

export { API_URL };
