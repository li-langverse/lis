"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

type ProjectDetail = {
  id: string;
  name: string;
  region: string;
  status: string;
  dbHealthy?: boolean;
  dataDir: string;
  ports: { api: number; db: number; realtime: number };
  urls?: { registry?: string; realtime_ws?: string };
};

export default function ProjectDashboardPage() {
  const params = useParams();
  const projectId = String(params.projectId ?? "");
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [launching, setLaunching] = useState(false);
  const [launchMessage, setLaunchMessage] = useState<string | null>(null);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/projects/${projectId}`, { cache: "no-store" });
      const json = (await res.json()) as { project?: ProjectDetail };
      setProject(json.project ?? null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function launchDatabase() {
    setLaunching(true);
    setLaunchMessage(null);
    setLaunchError(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/launch`, { method: "POST" });
      const json = (await res.json()) as { ok?: boolean; message?: string; error?: string; hint?: string };
      if (!res.ok || !json.ok) {
        setLaunchError([json.error, json.hint].filter(Boolean).join(" — "));
        return;
      }
      setLaunchMessage(json.message ?? "Database launched");
      await refresh();
    } catch (err) {
      setLaunchError(err instanceof Error ? err.message : String(err));
    } finally {
      setLaunching(false);
    }
  }

  return (
    <section className="panel">
      <header className="home-header">
        <div>
          <h1>{project?.name ?? "Project"}</h1>
          <p className="hint">
            {project?.region ?? "…"} · Isolated LI_DATA_DIR ·{" "}
            {project?.dbHealthy ? "Database healthy" : "Database stopped"}
          </p>
        </div>
        <div className="landing-actions">
          <button type="button" className="btn" onClick={() => void refresh()} disabled={loading}>
            Refresh
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void launchDatabase()}
            disabled={launching}
          >
            {launching ? "Launching…" : "Launch database"}
          </button>
        </div>
      </header>

      {launchMessage ? <p className="success-block">{launchMessage}</p> : null}
      {launchError ? <p className="error-block">{launchError}</p> : null}

      <div className="status-cards">
        <Link href={`/projects/${projectId}/database`} className={`status-card ${project?.dbHealthy ? "status-ok" : "status-warn"}`}>
          <span className="status-card-title">Database</span>
          <span className="status-card-value">{project?.dbHealthy ? "Healthy" : "Stopped"}</span>
          <span className="status-card-detail hint">Table editor and catalog browser</span>
        </Link>
        <Link href={`/projects/${projectId}/sql`} className="status-card status-ok">
          <span className="status-card-title">SQL Editor</span>
          <span className="status-card-value">Read-only</span>
          <span className="status-card-detail hint">SELECT queries against project lidb</span>
        </Link>
        <Link href={`/projects/${projectId}/settings`} className="status-card">
          <span className="status-card-title">Settings</span>
          <span className="status-card-value">Ports & paths</span>
          <span className="status-card-detail hint mono">{project?.dataDir ?? "…"}</span>
        </Link>
      </div>

      <h2 className="section-title">Connection</h2>
      <dl className="status-grid">
        <div className="status-row">
          <dt>registry</dt>
          <dd>{project?.urls?.registry ?? "—"}</dd>
        </div>
        <div className="status-row">
          <dt>realtime</dt>
          <dd>{project?.urls?.realtime_ws ?? "—"}</dd>
        </div>
        <div className="status-row">
          <dt>data_dir</dt>
          <dd>{project?.dataDir ?? "—"}</dd>
        </div>
      </dl>

      <p className="hint platform-note">
        Windows: set <code>LIS_DB_STATUS_SHELL=bash</code> and run from Git Bash/WSL. Docker per-project compose is planned in C3.
      </p>
    </section>
  );
}
