import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { NextResponse } from "next/server";
import { parseLisDbStatus, statusHealthy } from "@/lib/lis-db-status";
import { lisBin, lisRoot, statusShell } from "@/lib/lis-env";

const execFileAsync = promisify(execFile);

export async function GET() {
  const bin = lisBin();
  const shell = statusShell();

  try {
    const { stdout } = shell
      ? await execFileAsync(shell, [bin, "db", "status"], {
          cwd: lisRoot(),
          env: { ...process.env },
          timeout: 15_000,
        })
      : await execFileAsync(bin, ["db", "status"], {
          cwd: lisRoot(),
          env: { ...process.env },
          timeout: 15_000,
        });

    const lines = parseLisDbStatus(stdout);
    const ok = statusHealthy(lines);

    return NextResponse.json({
      ok,
      lines,
      raw: stdout,
      lis_root: lisRoot(),
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      {
        ok: false,
        lines: [],
        raw: "",
        error: message,
        lis_root: lisRoot(),
        hint: "Run `lis db start` from the lis repo, or set LIS_ROOT to your lis checkout.",
      },
      { status: 503 },
    );
  }
}
