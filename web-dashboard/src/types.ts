// src/types.ts
export type WindowSample = {
  id: number;
  timestamp: number; // unix seconds
  label: string;
  proba: number;
};

export type WindowSummary = {
  label: string | null;     // e.g. "studying" or null if no 70% majority
  confidence: number;       // fraction of windows that agree (0–1)
  window_count: number;
};

export type WindowsResponse = {
  windows: WindowSample[];
  summary: WindowSummary;
  server_time: number;
};
