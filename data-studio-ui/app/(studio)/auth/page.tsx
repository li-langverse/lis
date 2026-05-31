"use client";

import { useEffect, useState } from "react";
import { DataGrid } from "@/components/data-grid";

type Health = {
  ok?: boolean;
  backend?: string;
  stub?: boolean;
  error?: string;
  hint?: string;
};

type PackageRow = Record<string, unknown>;

export default function AuthPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [packages, setPackages] = useState<PackageRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);

  useEffect(() => {
    void (async () => {
      const [hRes, pRes] = await Promise.all([
        fetch("/api/registry/health", { cache: "no-store" }),
        fetch("/api/registry/packages?limit=25", { cache: "no-store" }),
      ]);
      setHealth((await hRes.json()) as Health);
      const pkg = (await pRes.json()) as { packages?: PackageRow[] };
      const rows = pkg.packages ?? [];
      setPackages(rows);
      if (rows.length) setColumns(Object.keys(rows[0]));
    })();
  }, []);

  return (
    <section className="panel">
      <h1>Authentication</h1>
      <p className="hint">
        Registry-min uses publisher tokens for publish/yank. Full lip SSO ships later (PH-DB-4+).
      </p>
      <p>
        Registry API{" "}
        <span className={`badge ${health?.ok ? "badge-ok" : "badge-warn"}`}>
          {health?.ok ? "reachable" : "unreachable"}
        </span>
        {health?.backend ? <> — backend: <code>{health.backend}</code></> : null}
      </p>
      {health?.error ? (
        <p className="error-block">
          {health.error}
          {health.hint ? ` — ${health.hint}` : null}
        </p>
      ) : null}
      <h2 className="section-title">RLS</h2>
      <p className="hint">
        Row-level security filters Realtime delivery via JWT claims. See{" "}
        <a href="https://github.com/li-langverse/lis/blob/main/docs/realtime.md" target="_blank" rel="noreferrer">
          lis realtime docs
        </a>{" "}
        and{" "}
        <a
          href="https://github.com/li-langverse/lidb/blob/main/docs/ph-db-4-registry-gap.md"
          target="_blank"
          rel="noreferrer"
        >
          lidb registry RLS notes
        </a>
        .
      </p>
      <h2 className="section-title">Published packages (registry)</h2>
      <DataGrid columns={columns} rows={packages} emptyMessage="No packages or registry API stopped." />
    </section>
  );
}
