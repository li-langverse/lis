"use client";

import { useEffect, useState } from "react";

type SettingsPayload = {
  ok: boolean;
  lis_root?: string;
  data_dir?: string;
  profile?: string;
  ports?: Record<string, string>;
  urls?: Record<string, string>;
  jwt?: { secret: string; audience: string; issuer: string };
  rls?: { enabled: boolean; docs: string };
  storage?: { configured: boolean; backend: string };
};

export default function SettingsPage() {
  const [data, setData] = useState<SettingsPayload | null>(null);

  useEffect(() => {
    void fetch("/api/settings", { cache: "no-store" })
      .then((r) => r.json())
      .then((j) => setData(j as SettingsPayload));
  }, []);

  return (
    <section className="panel">
      <h1>Settings</h1>
      <p className="hint">Project configuration from environment (read-only).</p>
      {!data ? (
        <p className="hint">Loading…</p>
      ) : (
        <dl className="status-grid">
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
            <dt>jwt_audience</dt>
            <dd>{data.jwt?.audience}</dd>
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
