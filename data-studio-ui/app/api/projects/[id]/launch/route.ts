import { NextResponse } from "next/server";
import { getProject, updateProject } from "@/lib/projects-store";
import { launchProjectDb } from "@/lib/project-runtime";

type Params = { params: Promise<{ id: string }> };

export async function POST(_request: Request, { params }: Params) {
  const { id } = await params;
  const project = await getProject(id);
  if (!project) {
    return NextResponse.json({ ok: false, error: "Project not found" }, { status: 404 });
  }

  const result = await launchProjectDb(project);
  await updateProject(id, { status: result.ok ? "running" : "unknown" });

  if (!result.ok) {
    return NextResponse.json(
      {
        ok: false,
        error: result.error ?? result.message,
        hint:
          process.platform === "win32"
            ? "On Windows, set LIS_DB_STATUS_SHELL=bash and run via WSL/Git Bash. Docker Desktop required for container path."
            : "Ensure lis bin/lis is executable and LIDB_ROOT points to a built lidb checkout.",
        recovery: [
          "Set LIS_ROOT to your lis checkout",
          "Set LIDB_ROOT to sibling lidb with native embed built",
          `Project data dir: ${project.dataDir}`,
        ],
      },
      { status: 503 },
    );
  }

  return NextResponse.json({
    ok: true,
    message: result.message,
    projectId: id,
    dataDir: project.dataDir,
    ports: project.ports,
  });
}
