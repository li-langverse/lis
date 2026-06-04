export type StudioNavItem = {
  href: string;
  label: string;
  section: string;
};

/** Librebase Studio primary navigation. */
export const STUDIO_NAV: StudioNavItem[] = [
  { href: "/database", label: "Database", section: "Database" },
  { href: "/sql", label: "SQL Editor", section: "SQL" },
  { href: "/auth", label: "Authentication", section: "Auth" },
  { href: "/storage", label: "Storage", section: "Storage" },
  { href: "/realtime", label: "Realtime", section: "Realtime" },
  { href: "/logs", label: "Logs", section: "Logs" },
  { href: "/settings", label: "Settings", section: "Settings" },
];
