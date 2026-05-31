"use client";

import { useCallback, useEffect, useState } from "react";
import { DataGrid } from "@/components/data-grid";

type CatalogTable = {
  key: string;
  columns: string[];
};

type RowsPayload = {
  ok: boolean;
  columns?: string[];
  rows?: Record<string, unknown>[];
  error?: string;
};

type RunSummary = {
  run_id: string;
  agent_id?: string;
  status?: string;
  started_at?: string;
  briefing_hash?: string;
};

type AgentsPayload = {
  ok: boolean;
  runs?: RunSummary[];
  active?: RunSummary[];
  dashboard_url?: string;
  error?: string;
  hint?: string;
};

export default function AgentsPage() {
  const [tables, setTables] = useState<CatalogTable[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [rows, setRows] = useState<RowsPayload | null>(null);
  const [rowsLoading, setRowsLoading] = useState(false);
  const [agents, setAgents] = useState<AgentsPayload | null>(null);
  const [traceRunId, setTraceRunId] = useState<string | null>(null);

  const loadCatalog = useCallback(async () => {
    const res = await fetch("/api/control-plane/tables", { cache: "no-store" });
    const json = (await res.json()) as { tables?: CatalogTable[] };
    setTables(json.tables ?? []);
  }, []);

  const loadAgents = useCallback(async () => {
    const res = await fetch("/api/agents/runs", { cache: "no-store" });
    setAgents((await res.json()) as AgentsPayload);
  }, []);

  const loadRows = useCallback(async (tableKey: string) => {
    setSelected(tableKey);
    setRowsLoading(true);
    try {
      const res = await fetch(`/api/db/tables/${encodeURIComponent(tableKey)}/rows?limit=50`, {
        cache: "no-store",
      });
      setRows((await res.json()) as RowsPayload);
    } catch (e) {
      setRows({ ok: false, error: e instanceof Error ? e.message : String(e) });
    } finally {
      setRowsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCatalog();
    void loadAgents();
  }, [loadCatalog, loadAgents]);

  const liveRuns = [...(agents?.active ?? []), ...(agents?.runs ?? [])].slice(0, 12);

  return (
    <section className="panel">
      <h1>Agents &amp; Control Plane</h1>
      <p className="hint">
        Live agent trace (via dashboard proxy) plus read-only control-plane tables from lidb — beats Supabase
        with cross-linked runs and honest degraded modes.
      </p>

      <div className="agents-layout">
        <aside className="trace-panel">
          <div className="trace-header">
            <h2 className="section-title">Live trace</h2>
            <button type="button" className="btn" onClick={() => void loadAgents()}>
              Refresh
            </button>
          </div>
          {!agents?.ok ? (
            <div className="error-block">
              {agents?.error ?? "Dashboard unreachable"}
              {agents?.hint ? ` — ${agents.hint}` : null}
              <ul className="recovery-list">
                <li>Start ops server: li-cursor-agents on port 9477</li>
                <li>Tables below still work via lidb embed</li>
              </ul>
            </div>
          ) : null}
          <ul className="run-list trace-list">
            {liveRuns.length === 0 ? (
              <li className="hint">No recent runs</li>
            ) : (
              liveRuns.map((run) => (
                <li key={run.run_id}>
                  <button
                    type="button"
                    className={`trace-run ${traceRunId === run.run_id ? "active" : ""}`}
                    onClick={() => {
                      setTraceRunId(run.run_id);
                      void loadRows("public.agent_runs");
                    }}
                  >
                    <span className="mono trace-run-id">{run.run_id}</span>
                    <span>{run.agent_id ?? "agent"}</span>
                    <span className={`badge ${run.status === "running" ? "badge-ok" : run.status === "error" ? "badge-danger" : "badge-warn"}`}>
                      {run.status ?? "?"}
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>
          {agents?.dashboard_url ? (
            <p className="hint">
              Full dashboard:{" "}
              <a href={agents.dashboard_url} target="_blank" rel="noreferrer">
                {agents.dashboard_url}
              </a>
            </p>
          ) : null}
        </aside>

        <div className="control-plane-main">
          <h2 className="section-title">Control-plane tables</h2>
          <div className="split-pane">
            <ul className="table-list">
              {tables.length === 0 ? (
                <li className="hint">No control-plane tables (is lidb running?)</li>
              ) : (
                tables.map((t) => (
                  <li key={t.key}>
                    <button
                      type="button"
                      className={`table-link ${selected === t.key ? "active" : ""}`}
                      onClick={() => void loadRows(t.key)}
                    >
                      <span className="mono">{t.key}</span>
                      <span className="hint table-col-count">{t.columns.length} cols</span>
                    </button>
                  </li>
                ))
              )}
            </ul>
            <div className="table-viewer">
              {selected ? (
                <>
                  <h3 className="mono">{selected}</h3>
                  {traceRunId && selected === "public.agent_runs" ? (
                    <p className="hint">Filtered view — select row matching run_id: {traceRunId}</p>
                  ) : null}
                  {rowsLoading ? (
                    <p className="hint">Loading rows…</p>
                  ) : rows?.error ? (
                    <p className="error-block">{rows.error}</p>
                  ) : (
                    <DataGrid
                      columns={rows?.columns ?? []}
                      rows={
                        traceRunId && selected === "public.agent_runs"
                          ? (rows?.rows ?? []).filter(
                              (r) => String(r.run_id ?? r.id ?? "") === traceRunId,
                            )
                          : (rows?.rows ?? [])
                      }
                      emptyMessage="Table is empty or embed unavailable."
                    />
                  )}
                </>
              ) : (
                <p className="hint">Select a control-plane table (read-only, limit 50).</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
