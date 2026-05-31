import { NextResponse } from "next/server";
import { getProject } from "@/lib/projects-store";
import { runProjectBridge } from "@/lib/project-bridge";

type Params = { params: Promise<{ id: string }> };

export async function POST(request: Request, { params }: Params) {
  const { id } = await params;
  const project = await getProject(id);
  if (!project) {
    return NextResponse.json({ ok: false, error: "Project not found" }, { status: 404 });
  }

  let body: { sql?: string };
  try {
    body = (await request.json()) as typeof body;
  } catch {
    return NextResponse.json({ ok: false, error: "Invalid JSON body" }, { status: 400 });
  }

  const sql = body.sql?.trim();
  if (!sql) {
    return NextResponse.json({ ok: false, error: "SQL is required" }, { status: 400 });
  }

  const result = await runProjectBridge(project, ["query", sql]);
  if (!result.ok) {
    return NextResponse.json(result, { status: 503 });
  }
  return NextResponse.json(result);
}
