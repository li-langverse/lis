"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

type SettingsPayload = {
  ok: boolean;
  project?: { id: string; name: string; region: string; orgId: string };
  lis_root?: string;
  data_dir?: string;
  profile?: string;
  ports?: Record<string, string>;
  urls?: Record<string, string>;
  jwt?: { secret: string; audience: string; issuer: string };
  rls?: { enabled: boolean; docs: string };
  storage?: { configured: boolean; backend: string };
};

export default function ProjectSettingsPage() {
  const params = useParams();
  const projectId = String(params.projectId ?? "");
  const [data, setData] = useState<SettingsPayload | null>(null);

  useEffect(() => {
    void fetch(`/api/projects/${projectId}/settings`, { cache: "no-store" })
      .then((r) => r.json())
      .then((j) => setData(j as SettingsPayload));
  }, [projectId]);

  return (
    <section className="panel">
      <h1>Settings</h1>
      <p className="hint">Project configuration — ports and paths allocated at creation time.</p>
      {!data ? (
        <p className="hint">Loading…</p>
      ) : (
        <dl className="status-grid">
          <div className="status-row">
            <dt>project</dt>
            <dd>{data.project?.name}</dd>
          </div>
          <div className="status-row">
            <dt>region</dt>
            <dd>{data.project?.region}</dd>
          </div>
          <div className="status-row">
            <dt>profile</dt>
            <dd>{data.profile}</dd>
          </div>
          <div className="status-row">
            <dt>data_dir</dt>
            <dd>{data.data_dir}</dd>
          </div>
          <div className="status-row">
            <dt>lis_root</dt>
            <dd>{data.lis_root}</dd>
          </div>
          {data.ports
            ? Object.entries(data.ports).map(([k, v]) => (
                <div key={k} className="status-row">
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))
            : null}
          <div className="status-row">
            <dt>jwt_secret</dt>
            <dd>{data.jwt?.secret}</dd>
          </div>
          <div className="status-row">
            <dt>rls</dt>
            <dd>
              {data.rls?.enabled ? "enabled" : "disabled"}{" "}
              (<a href={data.rls?.docs} target="_blank" rel="noreferrer">docs</a>)
            </dd>
          </div>
          <div className="status-row">
            <dt>storage</dt>
            <dd>{data.storage?.backend}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
