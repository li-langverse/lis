"use client";

import { useCallback, useEffect, useState } from "react";
import type { LisDbStatusLine } from "@/lib/lis-db-status";

type StatusPayload = {
  ok: boolean;
  lines: LisDbStatusLine[];
  raw: string;
  error?: string;
  hint?: string;
};

export default function DatabasePage() {
  const [data, setData] = useState<StatusPayload | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/db/status", { cache: "no-store" });
      const json = (await res.json()) as StatusPayload;
      setData(json);
    } catch (e) {
      setData({
        ok: false,
        lines: [],
        raw: "",
        error: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <section className="panel">
      <h1>Database</h1>
      <p className="hint">
        Supervisor health from <code>lis db status</code> (lidb embed probe). Table editor ships in WP-S2.
      </p>
      <p>
        <span className={`badge ${data?.ok ? "badge-ok" : "badge-warn"}`}>
          {loading ? "Checking…" : data?.ok ? "Healthy" : "Degraded / stopped"}
        </span>{" "}
        <button type="button" onClick={() => void refresh()} style={{ marginLeft: "0.5rem" }}>
          Refresh
        </button>
      </p>
      {data?.error ? (
        <p className="error-block">
          {data.error}
          {data.hint ? ` — ${data.hint}` : null}
        </p>
      ) : null}
      {data?.lines?.length ? (
        <dl className="status-grid">
          {data.lines.map((row) => (
            <div key={row.key} className="status-row">
              <dt>{row.key}</dt>
              <dd>{row.value}</dd>
            </div>
          ))}
        </dl>
      ) : !loading && !data?.error ? (
        <p className="hint">No status lines returned.</p>
      ) : null}
    </section>
  );
}
