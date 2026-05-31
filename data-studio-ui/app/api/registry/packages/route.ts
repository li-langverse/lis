import { NextRequest, NextResponse } from "next/server";
import { registryBaseUrl } from "@/lib/lis-env";

export async function GET(req: NextRequest) {
  const base = registryBaseUrl();
  const qs = req.nextUrl.searchParams.toString();
  const url = `${base}/v1/packages${qs ? `?${qs}` : ""}`;
  try {
    const res = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(10_000) });
    const body = await res.json();
    return NextResponse.json({ ok: res.ok, url, ...(body as object) }, { status: res.status });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ ok: false, url, error: message }, { status: 503 });
  }
}
