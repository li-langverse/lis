import { NextResponse } from "next/server";
import { parseLisDbStatus } from "@/lib/lis-db-status";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { lisBin, lisRoot, realtimeWsUrl, statusShell } from "@/lib/lis-env";

const execFileAsync = promisify(execFile);

export async function GET() {
  const wsUrl = realtimeWsUrl();
  let supervisor = "unknown";

  try {
    const shell = statusShell();
    const bin = lisBin();
    const { stdout } = shell
      ? await execFileAsync(shell, [bin, "db", "status"], { cwd: lisRoot(), timeout: 10_000 })
      : await execFileAsync(bin, ["db", "status"], { cwd: lisRoot(), timeout: 10_000 });
    const lines = parseLisDbStatus(stdout);
    supervisor = lines.find((l) => l.key === "realtime_ws")?.value ?? "unknown";
  } catch {
    supervisor = "status unavailable";
  }

  const running = supervisor.startsWith("running");
  return NextResponse.json({
    ok: running,
    ws_url: wsUrl,
    supervisor,
    profile_note: "Realtime starts with LI_PROFILE=stack-full or LI_REALTIME_API=1.",
    docs: "https://github.com/li-langverse/lis/blob/main/docs/realtime.md",
  });
}
