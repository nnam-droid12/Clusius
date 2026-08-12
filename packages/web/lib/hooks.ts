"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api-client";
import type { RunCreateInput } from "./types";

export function useRuns() {
  return useQuery({ queryKey: ["runs"], queryFn: api.listRuns, refetchInterval: 5_000 });
}

export function useResults() {
  return useQuery({ queryKey: ["results"], queryFn: api.listResults });
}

export function useRun(id: string) {
  return useQuery({
    queryKey: ["runs", id],
    queryFn: () => api.getRun(id),
    refetchInterval: (query) => (query.state.data?.status === "completed" ? false : 3_000),
  });
}

export function useCreateRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: RunCreateInput) => api.createRun(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}
