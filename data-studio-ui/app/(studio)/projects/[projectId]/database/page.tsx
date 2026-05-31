"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { DataGrid } from "@/components/data-grid";
import type { LisDbStatusLine } from "@/lib/lis-db-status";

type StatusPayload = {
  ok: boolean;
  lines: LisDbStatusLine[];
  raw: string;
  error?: string;
  hint?: string;
};

type CatalogTable = {
  schema: string;
  name: string;
  key: string;
  columns: string[];
};

type RowsPayload = {
  ok: boolean;
  columns?: string[];
  rows?: Record<string, unknown>[];
  error?: string;
};

export default function ProjectDatabasePage() {
  const params = useParams();
  const projectId = String(params.projectId ?? "");
  const apiBase = `/api/projects/${projectId}/db`;

  const [data, setData] = useState<StatusPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [tables, setTables] = useState<CatalogTable[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [rows, setRows] = useState<RowsPayload | null>(null);
  const [rowsLoading, setRowsLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/status`, { cache: "no-store" });
      setData((await res.json()) as StatusPayload);
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
  }, [apiBase]);

  const loadCatalog = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/tables`, { cache: "no-store" });
      const json = (await res.json()) as { tables?: CatalogTable[] };
      setTables(json.tables ?? []);
    } catch {
      setTables([]);
    }
  }, [apiBase]);

  const loadRows = useCallback(
    async (tableKey: string) => {
      setSelected(tableKey);
      setRowsLoading(true);
      try {
        const res = await fetch(
          `${apiBase}/tables/${encodeURIComponent(tableKey)}/rows?limit=100`,
          { cache: "no-store" },
        );
        setRows((await res.json()) as RowsPayload);
      } catch (e) {
        setRows({ ok: false, error: e instanceof Error ? e.message : String(e) });
      } finally {
        setRowsLoading(false);
      }
    },
    [apiBase],
  );

  useEffect(() => {
    void refresh();
    void loadCatalog();
  }, [refresh, loadCatalog]);

  return (
    <section className="panel">
      <h1>Database</h1>
      <p className="hint">Project-scoped supervisor health and read-only table browser.</p>
      <p>
        <span className={`badge ${data?.ok ? "badge-ok" : "badge-warn"}`}>
          {loading ? "Checking…" : data?.ok ? "Healthy" : "Degraded / stopped"}
        </span>{" "}
        <button type="button" className="btn" onClick={() => void refresh()}>
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
      ) : null}

      <h2 className="section-title">Tables</h2>
      <div className="split-pane">
        <ul className="table-list">
          {tables.length === 0 ? (
            <li className="hint">No catalog tables — launch the project database first.</li>
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
              {rowsLoading ? (
                <p className="hint">Loading rows…</p>
              ) : rows?.error ? (
                <p className="error-block">{rows.error}</p>
              ) : (
                <DataGrid
                  columns={rows?.columns ?? []}
                  rows={rows?.rows ?? []}
                  emptyMessage="Table is empty or embed unavailable."
                />
              )}
            </>
          ) : (
            <p className="hint">Select a table to preview rows (read-only, limit 100).</p>
          )}
        </div>
      </div>
    </section>
  );
}
