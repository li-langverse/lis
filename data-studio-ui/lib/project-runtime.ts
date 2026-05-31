import { execFile } from "node:child_process";
import { promisify } from "node:util";
import type { StudioProject } from "@/lib/projects-store";
import { lisBin, lisRoot, statusShell } from "@/lib/lis-env";
import { parseLisDbStatus, statusHealthy } from "@/lib/lis-db-status";

const execFileAsync = promisify(execFile);

export function projectProcessEnv(project: StudioProject): NodeJS.ProcessEnv {
  return {
    ...process.env,
    LI_DATA_DIR: project.dataDir,
    LI_API_PORT: String(project.ports.api),
    LI_DB_PORT: String(project.ports.db),
    LI_REALTIME_PORT: String(project.ports.realtime),
    LI_PROFILE: process.env.LI_PROFILE ?? "registry-min",
  };
}

export async function probeProjectDb(project: StudioProject): Promise<{
  ok: boolean;
  lines: ReturnType<typeof parseLisDbStatus>;
  raw: string;
  error?: string;
}> {
  const bin = lisBin();
  const shell = statusShell();
  const env = projectProcessEnv(project);

  try {
    const { stdout } = shell
      ? await execFileAsync(shell, [bin, "db", "status"], {
          cwd: lisRoot(),
          env,
          timeout: 15_000,
        })
      : await execFileAsync(bin, ["db", "status"], {
          cwd: lisRoot(),
          env,
          timeout: 15_000,
        });

    const lines = parseLisDbStatus(stdout);
    return { ok: statusHealthy(lines), lines, raw: stdout };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { ok: false, lines: [], raw: "", error: message };
  }
}

export async function launchProjectDb(project: StudioProject): Promise<{
  ok: boolean;
  message: string;
  error?: string;
}> {
  const bin = lisBin();
  const shell = statusShell();
  const env = projectProcessEnv(project);

  try {
    if (shell) {
      await execFileAsync(shell, [bin, "db", "start"], {
        cwd: lisRoot(),
        env,
        timeout: 120_000,
      });
    } else {
      await execFileAsync(bin, ["db", "start"], {
        cwd: lisRoot(),
        env,
        timeout: 120_000,
      });
    }

    const probe = await probeProjectDb(project);
    return {
      ok: probe.ok,
      message: probe.ok
        ? `Database running for ${project.name}`
        : "Start command finished but health check is degraded",
      error: probe.error,
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      message: "Failed to launch database",
      error: message,
    };
  }
}

export function projectRegistryUrl(project: StudioProject): string {
  const host = process.env.LI_API_HOST ?? "127.0.0.1";
  return `http://${host}:${project.ports.api}`;
}

export function projectRealtimeWsUrl(project: StudioProject): string {
  const host = process.env.LI_REALTIME_HOST ?? "127.0.0.1";
  return `ws://${host}:${project.ports.realtime}/realtime/v1/websocket`;
}
