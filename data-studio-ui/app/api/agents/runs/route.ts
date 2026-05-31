import { NextResponse } from "next/server";
import { agentsDashboardBaseUrl } from "@/lib/agents-env";

export async function GET() {
  const base = agentsDashboardBaseUrl();
  try {
    const res = await fetch(`${base}/api/runs`, {
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
    const body = (await res.json()) as Record<string, unknown>;
    return NextResponse.json({
      ok: res.ok,
      url: `${base}/api/runs`,
      dashboard_url: base,
      ...body,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      {
        ok: false,
        url: `${base}/api/runs`,
        runs: [],
        active: [],
        error: message,
        hint: "Agent dashboard unreachable — control-plane tables still available via lidb.",
      },
      { status: 503 },
    );
  }
}
