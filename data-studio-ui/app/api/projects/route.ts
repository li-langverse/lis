import { NextResponse } from "next/server";
import { createProject, listProjects } from "@/lib/projects-store";
import { probeProjectDb } from "@/lib/project-runtime";
import { allowedStudioRegions } from "@/lib/regions";

export async function GET() {
  const projects = await listProjects();
  const enriched = await Promise.all(
    projects.map(async (project) => {
      const probe = await probeProjectDb(project);
      return {
        ...project,
        status: probe.ok ? ("running" as const) : ("stopped" as const),
        dbHealthy: probe.ok,
      };
    }),
  );
  const regions = await allowedStudioRegions();
  return NextResponse.json({ ok: true, projects: enriched, regions });
}

export async function POST(request: Request) {
  let body: { name?: string; region?: string; orgId?: string };
  try {
    body = (await request.json()) as typeof body;
  } catch {
    return NextResponse.json({ ok: false, error: "Invalid JSON body" }, { status: 400 });
  }

  const name = body.name?.trim();
  if (!name) {
    return NextResponse.json({ ok: false, error: "Project name is required" }, { status: 400 });
  }

  const allowedRegions = await allowedStudioRegions();
  const region = body.region?.trim() || allowedRegions[0] || "local";
  if (!allowedRegions.includes(region)) {
    return NextResponse.json({ ok: false, error: "Invalid region" }, { status: 400 });
  }

  const project = await createProject({ name, region, orgId: body.orgId });
  return NextResponse.json({ ok: true, project }, { status: 201 });
}
