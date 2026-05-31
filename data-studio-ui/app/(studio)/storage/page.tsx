"use client";

import { useEffect, useState } from "react";

type StorageInfo = {
  storage?: { configured: boolean; backend: string };
};

export default function StoragePage() {
  const [data, setData] = useState<StorageInfo | null>(null);

  useEffect(() => {
    void fetch("/api/settings", { cache: "no-store" })
      .then((r) => r.json())
      .then((j) => setData(j as StorageInfo));
  }, []);

  const configured = data?.storage?.configured;

  return (
    <section className="panel">
      <h1>Storage</h1>
      <p className="hint">Object storage (li-storage) is not bundled in registry-min profile.</p>
      <p>
        <span className={`badge ${configured ? "badge-ok" : "badge-warn"}`}>
          {configured ? "configured" : "not configured"}
        </span>
      </p>
      <dl className="status-grid">
        <div className="status-row">
          <dt>backend</dt>
          <dd>{data?.storage?.backend ?? "loading…"}</dd>
        </div>
      </dl>
      <p className="hint">
        To enable storage, opt into a stack profile with li-storage and set LI_STORAGE_BUCKET / backend env vars.
      </p>
    </section>
  );
}
