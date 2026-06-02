import { randomUUID } from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";

export type ProjectStatus = "stopped" | "running" | "unknown";

export type StudioProject = {
  id: string;
  orgId: string;
  name: string;
  region: string;
  dataDir: string;
  ports: {
    api: number;
    db: number;
    realtime: number;
  };
  status: ProjectStatus;
  createdAt: string;
  updatedAt: string;
};

type ProjectStore = {
  version: 1;
  nextPortOffset: number;
  projects: StudioProject[];
};

export function projectsStorePath(): string {
  if (process.env.STUDIO_PROJECTS_FILE) return process.env.STUDIO_PROJECTS_FILE;
  const base = process.env.STUDIO_DATA_DIR ?? path.join(os.homedir(), ".local", "share", "lis", "studio");
  return path.join(base, "projects.json");
}

function defaultStore(): ProjectStore {
  return { version: 1, nextPortOffset: 0, projects: [] };
}

async function readStore(): Promise<ProjectStore> {
  const file = projectsStorePath();
  try {
    const raw = await fs.readFile(file, "utf8");
    const parsed = JSON.parse(raw) as ProjectStore;
    if (!parsed.projects) return defaultStore();
    return parsed;
  } catch {
    return defaultStore();
  }
}

async function writeStore(store: ProjectStore): Promise<void> {
  const file = projectsStorePath();
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, `${JSON.stringify(store, null, 2)}\n`, "utf8");
}

function projectDataDir(id: string): string {
  const base = process.env.STUDIO_DATA_DIR ?? path.join(os.homedir(), ".local", "share", "lis", "studio");
  return path.join(base, "projects", id, "data");
}

function allocatePorts(store: ProjectStore): StudioProject["ports"] {
  const offset = store.nextPortOffset;
  store.nextPortOffset += 20;
  const base = 55000 + offset;
  return { api: base, db: base + 1, realtime: base + 2 };
}

export async function listProjects(): Promise<StudioProject[]> {
  const store = await readStore();
  return store.projects.slice().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export async function getProject(id: string): Promise<StudioProject | null> {
  const store = await readStore();
  return store.projects.find((p) => p.id === id) ?? null;
}

export async function createProject(input: {
  name: string;
  region: string;
  orgId?: string;
}): Promise<StudioProject> {
  const store = await readStore();
  const id = randomUUID();
  const now = new Date().toISOString();
  const project: StudioProject = {
    id,
    orgId: input.orgId ?? "default",
    name: input.name.trim(),
    region: input.region,
    dataDir: projectDataDir(id),
    ports: allocatePorts(store),
    status: "stopped",
    createdAt: now,
    updatedAt: now,
  };
  store.projects.push(project);
  await fs.mkdir(project.dataDir, { recursive: true });
  await writeStore(store);
  return project;
}

export async function updateProject(
  id: string,
  patch: Partial<Pick<StudioProject, "name" | "region" | "status">>,
): Promise<StudioProject | null> {
  const store = await readStore();
  const idx = store.projects.findIndex((p) => p.id === id);
  if (idx < 0) return null;
  const current = store.projects[idx]!;
  const updated: StudioProject = {
    ...current,
    ...patch,
    updatedAt: new Date().toISOString(),
  };
  store.projects[idx] = updated;
  await writeStore(store);
  return updated;
}
