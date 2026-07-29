"use client";

import { useEffect, useState } from "react";

import { api } from "./api-client";
import type { RunEvent } from "./types";

export function useRunEvents(runId: string | null) {
  const [events, setEvents] = useState<RunEvent[]>([]);

  useEffect(() => {
    if (!runId) return;
    setEvents([]);

    const source = new EventSource(api.eventsUrl(runId));
    source.onmessage = (message) => {
      try {
        const parsed = JSON.parse(message.data) as RunEvent;
        setEvents((prev) => [...prev, parsed]);
      } catch {
        // keep-alive comments and malformed frames are silently dropped
      }
    };
    source.onerror = () => {
      source.close();
    };

    return () => source.close();
  }, [runId]);

  return events;
}
