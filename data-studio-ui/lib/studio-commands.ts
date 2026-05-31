import { STUDIO_NAV } from "@/lib/studio-nav";

export type StudioCommand = {
  id: string;
  label: string;
  section: string;
  keywords?: string;
  href?: string;
  action?: "refresh" | "palette-hint";
};

export const STUDIO_COMMANDS: StudioCommand[] = [
  {
    id: "nav-home",
    label: "Go to Projects",
    section: "Navigate",
    keywords: "home projects dashboard",
    href: "/",
  },
  ...STUDIO_NAV.map((item) => ({
    id: `nav-${item.href}`,
    label: `Go to ${item.label}`,
    section: "Navigate",
    keywords: item.label.toLowerCase(),
    href: item.href,
  })),
  {
    id: "action-refresh-db",
    label: "Refresh database status",
    section: "Actions",
    keywords: "reload health lis db",
    action: "refresh",
  },
  {
    id: "hint-palette",
    label: "Command palette help",
    section: "Help",
    keywords: "keyboard shortcut cmd ctrl k",
    action: "palette-hint",
  },
];

export function filterCommands(query: string): StudioCommand[] {
  const q = query.trim().toLowerCase();
  if (!q) return STUDIO_COMMANDS;
  return STUDIO_COMMANDS.filter((cmd) => {
    const hay = `${cmd.label} ${cmd.section} ${cmd.keywords ?? ""}`.toLowerCase();
    return q.split(/\s+/).every((token) => hay.includes(token));
  });
}
