import fs from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { defaultDataDir } from "@/lib/lis-env";

async function tailFile(filePath: string, maxLines = 80): Promise<string[]> {
  try {
    const raw = await fs.readFile(filePath, "utf8");
    return raw.split(/\r?\n/).filter(Boolean).slice(-maxLines);
  } catch {
    return [];
  }
}

export async function GET() {
  const dataDir = process.env.LI_DATA_DIR ?? defaultDataDir();
  const sources: { name: string; path: string; lines: string[] }[] = [];

  const candidates = [
    { name: "changefeed", path: path.join(dataDir, "wal.changefeed.jsonl") },
    { name: "supervisor", path: path.join(dataDir, "lis-db.log") },
    { name: "registry", path: path.join(dataDir, "lis-registry.log") },
  ];

  for (const c of candidates) {
    const lines = await tailFile(c.path);
    if (lines.length) sources.push({ ...c, lines });
  }

  let pidSummary = "";
  try {
    const pidFile = path.join(dataDir, "lis-db.pid");
    const pid = await fs.readFile(pidFile, "utf8");
    pidSummary = `supervisor pid ${pid.trim()}`;
  } catch {
    pidSummary = "supervisor not running";
  }

  return NextResponse.json({
    ok: true,
    data_dir: dataDir,
    pid_summary: pidSummary,
    sources,
    hint:
      sources.length === 0
        ? "No log files yet — start `lis db start` or enable LI_CHANGEFEED_NATIVE=0 JSONL."
        : undefined,
  });
}
