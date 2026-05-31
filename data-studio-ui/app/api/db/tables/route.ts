import { NextResponse } from "next/server";
import { runBridge } from "@/lib/run-bridge";

type CatalogTable = {
  schema: string;
  name: string;
  key: string;
  columns: string[];
};

export async function GET() {
  const result = await runBridge<{ tables?: CatalogTable[]; count?: number }>(["catalog"]);
  if (!result.ok) {
    return NextResponse.json(result, { status: 503 });
  }
  return NextResponse.json(result);
}
