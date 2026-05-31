import { NextRequest, NextResponse } from "next/server";
import { runBridge } from "@/lib/run-bridge";

type QueryPayload = {
  columns?: string[];
  rows?: Record<string, unknown>[];
  row_count?: number;
  limit?: number;
};

export async function POST(req: NextRequest) {
  let body: { sql?: string };
  try {
    body = (await req.json()) as { sql?: string };
  } catch {
    return NextResponse.json({ ok: false, error: "invalid JSON body" }, { status: 400 });
  }
  const sql = body.sql?.trim();
  if (!sql) {
    return NextResponse.json({ ok: false, error: "sql is required" }, { status: 400 });
  }
  const result = await runBridge<QueryPayload>(["query", sql]);
  if (!result.ok) {
    return NextResponse.json(result, { status: 400 });
  }
  return NextResponse.json(result);
}
