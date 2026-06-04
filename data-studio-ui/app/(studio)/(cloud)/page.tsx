"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type ProjectRow = {
  id: string;
  name: string;
  region: string;
  status: "stopped" | "running" | "unknown";
  dbHealthy?: boolean;
  ports: { api: number; db: number; realtime: number };
  updatedAt: string;
};

export default function ProjectsLandingPage() {
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/projects", { cache: "no-store" });
      const json = (await res.json()) as { projects?: ProjectRow[] };
      setProjects(json.projects ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <section className="panel landing-panel">
      <header className="landing-header">
        <div>
          <h1>Projects</h1>
          <p className="hint">
            Create a project, launch an isolated lidb stack, and open the modern data console for tables and SQL.
          </p>
        </div>
        <div className="landing-actions">
          <button type="button" className="btn" onClick={() => void refresh()} disabled={loading}>
            Refresh
          </button>
          <Link href="/projects/new" className="btn btn-primary">
            New project
          </Link>
        </div>
      </header>

      {loading && projects.length === 0 ? (
        <div className="project-grid">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="project-card project-card-skeleton" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <h2>No projects yet</h2>
          <p className="hint">Start by creating a project with its own data directory and port allocation.</p>
          <Link href="/projects/new" className="btn btn-primary">
            Create your first project
          </Link>
        </div>
      ) : (
        <div className="project-grid">
          {projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}`} className="project-card">
              <div className="project-card-head">
                <span className="project-card-name">{project.name}</span>
                <span
                  className={`badge ${project.dbHealthy ? "badge-ok" : project.status === "unknown" ? "badge-warn" : "badge-muted"}`}
                >
                  {project.dbHealthy ? "Running" : project.status === "unknown" ? "Unknown" : "Stopped"}
                </span>
              </div>
              <p className="project-card-meta hint">
                {project.region} · API :{project.ports.api}
              </p>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
