// src/useWindowStream.ts
import { useEffect, useState } from "react";
import type { WindowSample, WindowSummary, WindowsResponse } from "./types";

const API_BASE = "http://localhost:5000";

export function useWindowStream(pollMs = 300) {
  const [windows, setWindows] = useState<WindowSample[]>([]);
  const [summary, setSummary] = useState<WindowSummary | null>(null);
  const [lastServerTime, setLastServerTime] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    async function tick() {
      try {
        const params =
          lastServerTime != null ? `?since=${lastServerTime}` : "";
        const res = await fetch(`${API_BASE}/api/windows${params}`);
        const data: WindowsResponse = await res.json();

        if (cancelled) return;

        // append new windows
        setWindows(prev => [...prev, ...data.windows]);

        setSummary(data.summary);
        setLastServerTime(data.server_time);
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setError("Cannot reach backend");
        }
      } finally {
        if (!cancelled) {
          timer = window.setTimeout(tick, pollMs);
        }
      }
    }

    // start polling
    tick();

    return () => {
      cancelled = true;
      if (timer !== undefined) {
        clearTimeout(timer);
      }
    };
  }, [pollMs, lastServerTime]);

  return { windows, summary, error };
}
