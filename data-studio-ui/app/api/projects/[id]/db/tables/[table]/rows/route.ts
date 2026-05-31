import { NextResponse } from "next/server";
import { getProject } from "@/lib/projects-store";
import { runProjectBridge } from "@/lib/project-bridge";

type Params = { params: Promise<{ id: string; table: string }> };

export async function GET(request: Request, { params }: Params) {
  const { id, table } = await params;
  const project = await getProject(id);
  if (!project) {
    return NextResponse.json({ ok: false, error: "Project not found" }, { status: 404 });
  }

  const url = new URL(request.url);
  const limit = url.searchParams.get("limit") ?? "100";
  const result = await runProjectBridge(project, ["rows", table, limit]);
  if (!result.ok) {
    return NextResponse.json(result, { status: 503 });
  }
  return NextResponse.json(result);
}
