import type { StudioProject } from "@/lib/projects-store";
import { projectProcessEnv } from "@/lib/project-runtime";
import { bridgeScript, lisRoot, pythonCmd } from "@/lib/lis-env";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export type BridgeResult<T = Record<string, unknown>> = T & {
  ok: boolean;
  error?: string;
};

export async function runProjectBridge<T = Record<string, unknown>>(
  project: StudioProject,
  args: string[],
): Promise<BridgeResult<T>> {
  const script = bridgeScript();
  const env: NodeJS.ProcessEnv = {
    ...projectProcessEnv(project),
    LIS_ROOT: lisRoot(),
  };

  try {
    const { stdout } = await execFileAsync(pythonCmd(), [script, ...args], {
      cwd: process.cwd(),
      env,
      timeout: 30_000,
      maxBuffer: 10 * 1024 * 1024,
    });
    return JSON.parse(stdout.trim()) as BridgeResult<T>;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { ok: false, error: message } as BridgeResult<T>;
  }
}
