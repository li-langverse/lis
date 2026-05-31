import { NextResponse } from "next/server";
import { registryBaseUrl } from "@/lib/lis-env";

export async function GET() {
  const base = registryBaseUrl();
  try {
    const res = await fetch(`${base}/health`, { cache: "no-store", signal: AbortSignal.timeout(5000) });
    const body = (await res.json()) as Record<string, unknown>;
    return NextResponse.json({ ok: res.ok, url: `${base}/health`, ...body });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      {
        ok: false,
        url: `${base}/health`,
        status: "unreachable",
        error: message,
        hint: "Start registry with `lis db start` (LI_REGISTRY_API=1).",
      },
      { status: 503 },
    );
  }
}
