"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type CardStatus = "loading" | "ok" | "warn" | "error";

type StatusCard = {
  id: string;
  title: string;
  status: CardStatus;
  value: string;
  detail?: string;
  href: string;
  recovery?: string[];
};

type RunSummary = {
  run_id?: string;
  agent_id?: string;
  status?: string;
  started_at?: string;
};

export default function HomePage() {
  const [cards, setCards] = useState<StatusCard[]>([]);
  const [recentRuns, setRecentRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [db, registry, realtime, agentsRt, agentsRuns] = await Promise.all([
        fetch("/api/db/status", { cache: "no-store" }).then((r) => r.json()),
        fetch("/api/registry/health", { cache: "no-store" }).then((r) => r.json()),
        fetch("/api/realtime/status", { cache: "no-store" }).then((r) => r.json()),
        fetch("/api/agents/runtime", { cache: "no-store" }).then((r) => r.json()),
        fetch("/api/agents/runs", { cache: "no-store" }).then((r) => r.json()),
      ]);

      const next: StatusCard[] = [
        {
          id: "database",
          title: "Database",
          status: db.ok ? "ok" : "warn",
          value: db.ok ? "Healthy" : "Degraded",
          detail: db.lines?.find((l: { key: string }) => l.key === "lidb")?.value ?? db.error,
          href: "/database",
          recovery: db.ok ? undefined : ["Run `lis db start` from the lis repo", "Set LIS_ROOT to your lis checkout"],
        },
        {
          id: "registry",
          title: "Registry API",
          status: registry.ok ? "ok" : "warn",
          value: registry.ok ? "Online" : "Unreachable",
          detail: registry.url ?? registry.error,
          href: "/auth",
          recovery: registry.ok ? undefined : ["Start with `lis db start` (LI_REGISTRY_API=1)"],
        },
        {
          id: "realtime",
          title: "Realtime",
          status: realtime.ok ? "ok" : "warn",
          value: realtime.ok ? "Running" : "Stopped",
          detail: realtime.supervisor,
          href: "/realtime",
        },
        {
          id: "agents",
          title: "Agent control plane",
          status: agentsRt.ok ? "ok" : "warn",
          value: agentsRt.ok
            ? `${String(agentsRt.control_plane_store ?? agentsRt.store ?? "connected")}`
            : "Offline",
          detail: agentsRt.async_swarm_running
            ? "Swarm running"
            : agentsRt.error ?? "Dashboard proxy unavailable",
          href: "/agents",
          recovery: agentsRt.ok
            ? undefined
            : (agentsRt.recovery as string[] | undefined) ?? [
                "Start li-cursor-agents ops server on :9477",
                "Browse control-plane tables via lidb when dashboard is down",
              ],
        },
      ];
      setCards(next);

      const runs = (agentsRuns.runs ?? agentsRuns.active ?? []) as RunSummary[];
      setRecentRuns(Array.isArray(runs) ? runs.slice(0, 5) : []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <section className="panel">
      <div className="home-header">
        <div>
          <h1>Project Home</h1>
          <p className="hint">
            Unified ops view — keyboard-first with <kbd>⌘K</kbd>. Beats Supabase Studio with agent trace +
            control-plane visibility.
          </p>
        </div>
        <button type="button" className="btn" onClick={() => void refresh()} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh all"}
        </button>
      </div>

      <div className="status-cards">
        {cards.map((card) => (
          <Link key={card.id} href={card.href} className={`status-card status-${card.status}`}>
            <span className="status-card-title">{card.title}</span>
            <span className="status-card-value">{card.value}</span>
            {card.detail ? <span className="status-card-detail hint">{card.detail}</span> : null}
            {card.recovery?.length ? (
              <ul className="recovery-list">
                {card.recovery.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            ) : null}
          </Link>
        ))}
        {loading && cards.length === 0
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="status-card status-loading">
                <span className="hint">Loading…</span>
              </div>
            ))
          : null}
      </div>

      <h2 className="section-title">Recent agent runs</h2>
      {recentRuns.length === 0 ? (
        <p className="hint">
          No live runs from dashboard proxy.{" "}
          <Link href="/agents">Browse control-plane tables</Link> or start the agents dashboard.
        </p>
      ) : (
        <ul className="run-list">
          {recentRuns.map((run) => (
            <li key={run.run_id ?? run.agent_id} className="run-list-item">
              <span className="mono">{run.run_id ?? "—"}</span>
              <span>{run.agent_id ?? "unknown agent"}</span>
              <span className={`badge ${run.status === "running" ? "badge-ok" : run.status === "error" ? "badge-danger" : "badge-warn"}`}>
                {run.status ?? "unknown"}
              </span>
            </li>
          ))}
        </ul>
      )}

      <h2 className="section-title">Quick actions</h2>
      <div className="quick-actions">
        <Link href="/database" className="btn">
          Table editor
        </Link>
        <Link href="/sql" className="btn">
          SQL editor
        </Link>
        <Link href="/agents" className="btn btn-primary">
          Agent trace
        </Link>
        <Link href="/logs" className="btn">
          Logs
        </Link>
      </div>
    </section>
  );
}
