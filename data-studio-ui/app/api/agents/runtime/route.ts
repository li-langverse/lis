import { NextResponse } from "next/server";
import { agentsDashboardBaseUrl } from "@/lib/agents-env";

export async function GET() {
  const base = agentsDashboardBaseUrl();
  try {
    const res = await fetch(`${base}/api/runtime`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    const body = (await res.json()) as Record<string, unknown>;
    return NextResponse.json({
      ok: res.ok,
      url: `${base}/api/runtime`,
      dashboard_url: base,
      ...body,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      {
        ok: false,
        url: `${base}/api/runtime`,
        dashboard_url: base,
        error: message,
        hint: "Start li-cursor-agents dashboard or set LI_AGENT_DASHBOARD_HOST/PORT.",
        recovery: [
          "cd li-cursor-agents && npm run dev:ops",
          "Or install systemd: li-cursor-agents/scripts/install-dashboard.sh",
        ],
      },
      { status: 503 },
    );
  }
}
