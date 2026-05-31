import { NextResponse } from "next/server";
import { createProject, listProjects, studioRegions } from "@/lib/projects-store";
import { probeProjectDb } from "@/lib/project-runtime";

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
  return NextResponse.json({ ok: true, projects: enriched, regions: studioRegions() });
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

  const allowedRegions = studioRegions();
  const region = body.region?.trim() || allowedRegions[0];
  if (!allowedRegions.includes(region as (typeof allowedRegions)[number])) {
    return NextResponse.json({ ok: false, error: "Invalid region" }, { status: 400 });
  }

  const project = await createProject({ name, region, orgId: body.orgId });
  return NextResponse.json({ ok: true, project }, { status: 201 });
}
