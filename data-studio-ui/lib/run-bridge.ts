import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { bridgeScript, defaultDataDir, lisRoot, pythonCmd } from "@/lib/lis-env";

const execFileAsync = promisify(execFile);

export type BridgeResult<T = Record<string, unknown>> = T & {
  ok: boolean;
  error?: string;
};

export async function runBridge<T = Record<string, unknown>>(
  args: string[],
): Promise<BridgeResult<T>> {
  const script = bridgeScript();
  const env = {
    ...process.env,
    LIS_ROOT: lisRoot(),
    LI_DATA_DIR: process.env.LI_DATA_DIR ?? defaultDataDir(),
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
