import path from "node:path";
import os from "node:os";

export function lisRoot(): string {
  return process.env.LIS_ROOT ?? path.resolve(process.cwd(), "..");
}

export function lisBin(): string {
  return path.join(lisRoot(), "bin", "lis");
}

export function defaultDataDir(): string {
  if (process.env.LI_DATA_DIR) return process.env.LI_DATA_DIR;
  const home = os.homedir();
  return path.join(home, ".local", "share", "lis", "data");
}

export function bridgeScript(): string {
  return path.join(process.cwd(), "scripts", "lidb_studio_bridge.py");
}

export function pythonCmd(): string {
  return process.env.LIS_PYTHON ?? (process.platform === "win32" ? "python" : "python3");
}

export function statusShell(): string | undefined {
  return process.env.LIS_DB_STATUS_SHELL ?? (process.platform === "win32" ? "bash" : undefined);
}

export function registryBaseUrl(): string {
  const port = process.env.LI_API_PORT ?? "54321";
  const host = process.env.LI_API_HOST ?? "127.0.0.1";
  return `http://${host}:${port}`;
}

export function realtimeWsUrl(): string {
  const port = process.env.LI_REALTIME_PORT ?? "54323";
  const host = process.env.LI_REALTIME_HOST ?? "127.0.0.1";
  return `ws://${host}:${port}/realtime/v1/websocket`;
}
