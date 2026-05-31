"use client";



import { useState } from "react";

import { DataGrid } from "@/components/data-grid";

import { rowsToCsv } from "@/lib/csv";



type QueryResult = {

  ok: boolean;

  columns?: string[];

  rows?: Record<string, unknown>[];

  row_count?: number;

  error?: string;

};



const DEFAULT_SQL = "SELECT id, version, yanked FROM package_versions LIMIT 20";



export default function SqlPage() {

  const [sql, setSql] = useState(DEFAULT_SQL);

  const [result, setResult] = useState<QueryResult | null>(null);

  const [running, setRunning] = useState(false);



  async function runQuery() {

    setRunning(true);

    try {

      const res = await fetch("/api/db/query", {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify({ sql }),

      });

      const json = (await res.json()) as QueryResult;

      setResult(json);

    } catch (e) {

      setResult({ ok: false, error: e instanceof Error ? e.message : String(e) });

    } finally {

      setRunning(false);

    }

  }



  function exportCsv() {

    if (!result?.columns?.length || !result.rows) return;

    const csv = rowsToCsv(result.columns, result.rows);

    const blob = new Blob([csv], { type: "text/csv" });

    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");

    a.href = url;

    a.download = "query-results.csv";

    a.click();

    URL.revokeObjectURL(url);

  }



  return (

    <section className="panel">

      <h1>SQL Editor</h1>

      <p className="hint">Read-only SELECT queries against lidb (max 500 rows). Mutations are blocked.</p>

      <textarea

        className="sql-input"

        value={sql}

        onChange={(e) => setSql(e.target.value)}

        rows={8}

        spellCheck={false}

        aria-label="SQL query"

      />

      <div className="toolbar">

        <button type="button" className="btn btn-primary" disabled={running} onClick={() => void runQuery()}>

          {running ? "Running…" : "Run"}

        </button>

        <button

          type="button"

          className="btn"

          disabled={!result?.ok || !result.rows?.length}

          onClick={exportCsv}

        >

          Export CSV

        </button>

      </div>

      {result?.error ? <p className="error-block">{result.error}</p> : null}

      {result?.ok ? (

        <p className="hint">{result.row_count ?? result.rows?.length ?? 0} row(s)</p>

      ) : null}

      {result?.columns ? (

        <DataGrid columns={result.columns} rows={result.rows ?? []} emptyMessage="Query returned no rows." />

      ) : null}

    </section>

  );

}

