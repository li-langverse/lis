import { NextResponse } from "next/server";
import { getProject } from "@/lib/projects-store";
import { probeProjectDb, projectRegistryUrl, projectRealtimeWsUrl } from "@/lib/project-runtime";

type Params = { params: Promise<{ id: string }> };

export async function GET(_request: Request, { params }: Params) {
  const { id } = await params;
  const project = await getProject(id);
  if (!project) {
    return NextResponse.json({ ok: false, error: "Project not found" }, { status: 404 });
  }

  const probe = await probeProjectDb(project);
  return NextResponse.json({
    ok: true,
    project: {
      ...project,
      status: probe.ok ? "running" : "stopped",
      dbHealthy: probe.ok,
      urls: {
        registry: `${projectRegistryUrl(project)}/v1`,
        realtime_ws: projectRealtimeWsUrl(project),
      },
    },
  });
}
