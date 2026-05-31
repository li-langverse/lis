import { NextRequest, NextResponse } from "next/server";
import { runBridge } from "@/lib/run-bridge";

type RowsPayload = {
  table?: string;
  columns?: string[];
  rows?: Record<string, unknown>[];
  limit?: number;
  offset?: number;
};

export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ table: string }> },
) {
  const { table } = await ctx.params;
  const limit = Math.min(Number(req.nextUrl.searchParams.get("limit") ?? 100), 500);
  const offset = Math.max(Number(req.nextUrl.searchParams.get("offset") ?? 0), 0);
  const decoded = decodeURIComponent(table);
  const result = await runBridge<RowsPayload>(["rows", decoded, String(limit), String(offset)]);
  if (!result.ok) {
    return NextResponse.json(result, { status: 503 });
  }
  return NextResponse.json(result);
}
