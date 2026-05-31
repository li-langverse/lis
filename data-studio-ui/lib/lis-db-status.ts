export type LisDbStatusLine = {
  key: string;
  value: string;
};

export type LisDbStatus = {
  ok: boolean;
  lines: LisDbStatusLine[];
  raw: string;
  error?: string;
};

/** Parse `lis db status` key: value lines. */
export function parseLisDbStatus(stdout: string): LisDbStatusLine[] {
  const lines: LisDbStatusLine[] = [];
  for (const row of stdout.split(/\r?\n/)) {
    const m = row.match(/^([a-z_]+):\s+(.*)$/);
    if (m) lines.push({ key: m[1], value: m[2].trim() });
  }
  return lines;
}

export function statusHealthy(parsed: LisDbStatusLine[]): boolean {
  const state = parsed.find((l) => l.key === "state")?.value ?? "";
  const link = parsed.find((l) => l.key === "lidb_link")?.value ?? "";
  return state.startsWith("running") && link.includes("native");
}
