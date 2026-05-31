import { NextResponse } from "next/server";
import { defaultDataDir, lisRoot, registryBaseUrl, realtimeWsUrl } from "@/lib/lis-env";

function maskSecret(value: string | undefined): string {
  if (!value) return "(not set)";
  if (value.length <= 8) return "••••••••";
  return `${value.slice(0, 4)}…${value.slice(-4)} (${value.length} chars)`;
}

export async function GET() {
  return NextResponse.json({
    ok: true,
    lis_root: lisRoot(),
    data_dir: process.env.LI_DATA_DIR ?? defaultDataDir(),
    profile: process.env.LI_PROFILE ?? "registry-min",
    ports: {
      registry_api: process.env.LI_API_PORT ?? "54321",
      db: process.env.LI_DB_PORT ?? "54322",
      realtime: process.env.LI_REALTIME_PORT ?? "54323",
      studio_ui: "54324",
    },
    urls: {
      registry: `${registryBaseUrl()}/v1`,
      realtime_ws: realtimeWsUrl(),
    },
    jwt: {
      secret: maskSecret(process.env.LI_JWT_SECRET ?? process.env.SUPABASE_JWT_SECRET),
      audience: process.env.LI_JWT_AUD ?? process.env.SUPABASE_JWT_AUD ?? "(default)",
      issuer: process.env.LI_JWT_ISS ?? "(not set)",
    },
    rls: {
      enabled: process.env.LI_RLS_ENABLED !== "0",
      docs: "https://github.com/li-langverse/lidb/blob/main/docs/ph-db-4-registry-gap.md",
    },
    storage: {
      configured: Boolean(process.env.LI_STORAGE_BUCKET),
      backend: process.env.LI_STORAGE_BACKEND ?? "none (registry-min excludes li-storage)",
    },
  });
}
