import { NextResponse } from "next/server";
import { getProject } from "@/lib/projects-store";
import { projectRegistryUrl, projectRealtimeWsUrl } from "@/lib/project-runtime";
import { lisRoot } from "@/lib/lis-env";

type Params = { params: Promise<{ id: string }> };

function maskSecret(value: string | undefined): string {
  if (!value) return "(not set)";
  if (value.length <= 8) return "********";
  return `${value.slice(0, 4)}…${value.slice(-4)} (${value.length} chars)`;
}

export async function GET(_request: Request, { params }: Params) {
  const { id } = await params;
  const project = await getProject(id);
  if (!project) {
    return NextResponse.json({ ok: false, error: "Project not found" }, { status: 404 });
  }

  return NextResponse.json({
    ok: true,
    project: {
      id: project.id,
      name: project.name,
      region: project.region,
      orgId: project.orgId,
    },
    lis_root: lisRoot(),
    data_dir: project.dataDir,
    profile: process.env.LI_PROFILE ?? "registry-min",
    ports: {
      registry_api: String(project.ports.api),
      db: String(project.ports.db),
      realtime: String(project.ports.realtime),
      studio_ui: "54324",
    },
    urls: {
      registry: `${projectRegistryUrl(project)}/v1`,
      realtime_ws: projectRealtimeWsUrl(project),
    },
    jwt: {
      secret: maskSecret(process.env.LI_JWT_SECRET ?? process.env.SUPABASE_JWT_SECRET),
      audience: process.env.LI_JWT_AUD ?? process.env.SUPABASE_JWT_AUD ?? "(default)",
      issuer: process.env.LI_JWT_ISS ?? "(not set)",
    },
    rls: {
      enabled: process.env.LI_RLS_ENABLED !== "0",
      docs: "https://github.com/li-langverse/lidb/blob/main/docs/ph-db-4-registry-gap.md",
    },
    storage: {
      configured: Boolean(process.env.LI_STORAGE_BUCKET),
      backend: process.env.LI_STORAGE_BACKEND ?? "none (registry-min excludes li-storage)",
    },
  });
}
