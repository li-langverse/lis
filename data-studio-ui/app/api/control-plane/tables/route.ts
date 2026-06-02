import { NextResponse } from "next/server";
import { CONTROL_PLANE_TABLES } from "@/lib/agents-env";
import { runBridge } from "@/lib/run-bridge";

type CatalogTable = {
  schema: string;
  name: string;
  key: string;
  columns: string[];
};

export async function GET() {
  const result = await runBridge<{ tables?: CatalogTable[] }>(["catalog"]);
  if (!result.ok) {
    return NextResponse.json(result, { status: 503 });
  }
  const allow = new Set<string>(CONTROL_PLANE_TABLES);
  const tables = (result.tables ?? []).filter((t) => allow.has(t.key));
  return NextResponse.json({ ok: true, tables, count: tables.length });
}
