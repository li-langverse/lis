import { NextResponse } from "next/server";
import { getProject } from "@/lib/projects-store";
import { probeProjectDb } from "@/lib/project-runtime";

type Params = { params: Promise<{ id: string }> };

export async function GET(_request: Request, { params }: Params) {
  const { id } = await params;
  const project = await getProject(id);
  if (!project) {
    return NextResponse.json({ ok: false, error: "Project not found" }, { status: 404 });
  }

  const probe = await probeProjectDb(project);
  return NextResponse.json({
    ok: probe.ok,
    lines: probe.lines,
    raw: probe.raw,
    error: probe.error,
    lis_root: process.env.LIS_ROOT,
    data_dir: project.dataDir,
    ports: project.ports,
    hint: probe.ok
      ? undefined
      : 'Click "Launch database" or run `lis db start` with this project LI_DATA_DIR.',
  });
}
