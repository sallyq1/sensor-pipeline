import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

// src/App.tsx
import { useWindowStream } from "./useWindowStream";

function App() {
  const { windows, summary, error } = useWindowStream(300);

  const currentLabel = summary?.label ?? "Waiting for consensus…";
  const consensusPct = summary
    ? (summary.confidence * 100).toFixed(1)
    : null;

  const recent = [...windows].slice(-10).reverse();

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#020617",
        color: "#e5e7eb",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <div
        style={{
          background: "#0f172a",
          padding: "1.5rem 2rem",
          borderRadius: "1rem",
          boxShadow: "0 20px 40px rgba(0,0,0,0.4)",
          width: "640px",
          maxWidth: "95%",
        }}
      >
        <div style={{ marginBottom: "0.5rem", fontSize: "0.8rem", color: "#9ca3af" }}>
          Live Activity Summary
        </div>

        <div style={{ fontSize: "2.2rem", fontWeight: 600 }}>
          {currentLabel}
        </div>

        {consensusPct && (
          <div style={{ marginTop: "0.25rem", fontSize: "0.9rem", color: "#cbd5f5" }}>
            Consensus: {consensusPct}% of recent windows
          </div>
        )}

        {error && (
          <div
            style={{
              marginTop: "0.75rem",
              fontSize: "0.85rem",
              color: "#fca5a5",
            }}
          >
            {error}
          </div>
        )}

        <hr
          style={{
            margin: "1rem 0",
            borderColor: "#1f2937",
            borderBottomWidth: 0,
            borderTopWidth: 1,
          }}
        />

        <div style={{ fontSize: "0.8rem", color: "#9ca3af", marginBottom: "0.25rem" }}>
          Recent classified windows
        </div>
        <div
          style={{
            maxHeight: "200px",
            overflowY: "auto",
            fontSize: "0.8rem",
            border: "1px solid #111827",
            borderRadius: "0.5rem",
          }}
        >
          {recent.map(w => (
            <div
              key={w.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "0.3rem 0.6rem",
                borderBottom: "1px solid #020617",
              }}
            >
              <span style={{ color: "#9ca3af" }}>
                {new Date(w.timestamp * 1000).toLocaleTimeString()}
              </span>
              <span style={{ fontWeight: 500 }}>{w.label}</span>
              <span style={{ color: "#a5b4fc" }}>
                {(w.proba * 100).toFixed(1)}%
              </span>
            </div>
          ))}
          {recent.length === 0 && (
            <div style={{ padding: "0.5rem 0.6rem", color: "#6b7280" }}>
              No windows yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
