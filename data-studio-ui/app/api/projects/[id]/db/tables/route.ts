import { NextResponse } from "next/server";
import { getProject } from "@/lib/projects-store";
import { runProjectBridge } from "@/lib/project-bridge";

type Params = { params: Promise<{ id: string }> };

type CatalogTable = {
  schema: string;
  name: string;
  key: string;
  columns: string[];
};

export async function GET(_request: Request, { params }: Params) {
  const { id } = await params;
  const project = await getProject(id);
  if (!project) {
    return NextResponse.json({ ok: false, error: "Project not found" }, { status: 404 });
  }

  const result = await runProjectBridge<{ tables?: CatalogTable[]; count?: number }>(project, ["catalog"]);
  if (!result.ok) {
    return NextResponse.json(result, { status: 503 });
  }
  return NextResponse.json(result);
}
