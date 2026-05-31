"use client";

import { ProjectShell } from "@/components/project-shell";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const projectId = String(params.projectId ?? "");
  const [projectName, setProjectName] = useState("Project");

  useEffect(() => {
    if (!projectId) return;
    void fetch(`/api/projects/${projectId}`, { cache: "no-store" })
      .then((r) => r.json())
      .then((j: { project?: { name?: string } }) => {
        if (j.project?.name) setProjectName(j.project.name);
      });
  }, [projectId]);

  return (
    <ProjectShell projectId={projectId} projectName={projectName}>
      {children}
    </ProjectShell>
  );
}
