export function agentsDashboardBaseUrl(): string {
  const port = process.env.LI_AGENT_DASHBOARD_PORT ?? process.env.LI_AGENTS_OPS_PORT ?? "9477";
  const host = process.env.LI_AGENT_DASHBOARD_HOST ?? "127.0.0.1";
  return `http://${host}:${port}`;
}

export const CONTROL_PLANE_TABLES = [
  "public.agent_runs",
  "public.agent_run_events",
  "public.queued_agent_tasks",
  "public.control_plane_state",
  "public.control_plane_reports",
  "public.briefing_snapshots",
  "public.repo_workflow_rollouts",
] as const;

export type ControlPlaneTableKey = (typeof CONTROL_PLANE_TABLES)[number];
