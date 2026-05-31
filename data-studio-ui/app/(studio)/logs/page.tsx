"use client";

import { useEffect, useState } from "react";

type LogSource = { name: string; path: string; lines: string[] };

type LogsPayload = {
  ok: boolean;
  data_dir?: string;
  pid_summary?: string;
  sources?: LogSource[];
  hint?: string;
};

export default function LogsPage() {
  const [data, setData] = useState<LogsPayload | null>(null);

  useEffect(() => {
    void fetch("/api/logs", { cache: "no-store" })
      .then((r) => r.json())
      .then((j) => setData(j as LogsPayload));
  }, []);

  return (
    <section className="panel">
      <h1>Logs</h1>
      <p className="hint">Tail changefeed JSONL and supervisor logs from LI_DATA_DIR.</p>
      {data?.pid_summary ? <p className="mono">{data.pid_summary}</p> : null}
      {data?.hint ? <p className="hint">{data.hint}</p> : null}
      {data?.sources?.length ? (
        data.sources.map((src) => (
          <div key={src.name} className="log-block">
            <h2 className="section-title">
              {src.name} <span className="hint mono">({src.path})</span>
            </h2>
            <pre className="log-pre">{src.lines.join("\n")}</pre>
          </div>
        ))
      ) : !data?.hint ? (
        <p className="hint">Loading…</p>
      ) : null}
    </section>
  );
}
