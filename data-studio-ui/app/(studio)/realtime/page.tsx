"use client";

import { useEffect, useState } from "react";

type RealtimeStatus = {
  ok: boolean;
  ws_url?: string;
  supervisor?: string;
  profile_note?: string;
  docs?: string;
};

export default function RealtimePage() {
  const [data, setData] = useState<RealtimeStatus | null>(null);

  useEffect(() => {
    void fetch("/api/realtime/status", { cache: "no-store" })
      .then((r) => r.json())
      .then((j) => setData(j as RealtimeStatus));
  }, []);

  return (
    <section className="panel">
      <h1>Realtime</h1>
      <p className="hint">Phoenix v1.0.0 WebSocket changefeed (Supabase-shaped subset).</p>
      <p>
        <span className={`badge ${data?.ok ? "badge-ok" : "badge-warn"}`}>
          {data?.ok ? "running" : "stopped"}
        </span>
      </p>
      {data ? (
        <dl className="status-grid">
          <div className="status-row">
            <dt>supervisor</dt>
            <dd>{data.supervisor}</dd>
          </div>
          <div className="status-row">
            <dt>ws_url</dt>
            <dd>{data.ws_url}</dd>
          </div>
          <div className="status-row">
            <dt>note</dt>
            <dd>{data.profile_note}</dd>
          </div>
        </dl>
      ) : (
        <p className="hint">Loading…</p>
      )}
      {data?.docs ? (
        <p>
          <a href={data.docs} target="_blank" rel="noreferrer">
            Realtime protocol docs
          </a>
        </p>
      ) : null}
    </section>
  );
}
