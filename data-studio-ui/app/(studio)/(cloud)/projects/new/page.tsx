"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [region, setRegion] = useState("us-east-1");
  const [regions, setRegions] = useState<string[]>(["us-east-1", "eu-west-1", "ap-southeast-1"]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetch("/api/projects")
      .then((r) => r.json())
      .then((j: { regions?: string[] }) => {
        if (j.regions?.length) setRegions(j.regions);
      });
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, region }),
      });
      const json = (await res.json()) as { ok?: boolean; project?: { id: string }; error?: string };
      if (!res.ok || !json.project?.id) {
        setError(json.error ?? "Failed to create project");
        return;
      }
      router.push(`/projects/${json.project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel form-panel">
      <Link href="/" className="breadcrumb">
        Projects
      </Link>
      <h1>New project</h1>
      <p className="hint">Each project gets an isolated LI_DATA_DIR and dedicated ports for lis db.</p>

      <form className="project-form" onSubmit={(e) => void onSubmit(e)}>
        <label className="field">
          <span>Name</span>
          <input
            className="text-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My app"
            required
            autoFocus
          />
        </label>
        <label className="field">
          <span>Region</span>
          <select className="text-input" value={region} onChange={(e) => setRegion(e.target.value)}>
            {regions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <span className="field-hint">Stub for future multi-region hosting (C1/C3).</span>
        </label>
        {error ? <p className="error-block">{error}</p> : null}
        <div className="form-actions">
          <Link href="/" className="btn">
            Cancel
          </Link>
          <button type="submit" className="btn btn-primary" disabled={submitting || !name.trim()}>
            {submitting ? "Creating…" : "Create project"}
          </button>
        </div>
      </form>
    </section>
  );
}
