"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const PROJECT_NAV = [
  { href: "overview", label: "Overview", suffix: "" },
  { href: "database", label: "Database", suffix: "/database" },
  { href: "sql", label: "SQL Editor", suffix: "/sql" },
  { href: "settings", label: "Settings", suffix: "/settings" },
] as const;

type Props = {
  projectId: string;
  projectName: string;
  children: React.ReactNode;
};

export function ProjectShell({ projectId, projectName, children }: Props) {
  const pathname = usePathname();
  const base = `/projects/${projectId}`;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link href="/" className="brand brand-link">
          Librebase Studio
        </Link>
        <div className="brand-sub project-context">
          <span className="project-label">Project</span>
          <span className="project-name">{projectName}</span>
        </div>
        <nav className="nav" aria-label="Project">
          {PROJECT_NAV.map((item) => {
            const href = item.suffix ? `${base}${item.suffix}` : base;
            const active =
              item.suffix === ""
                ? pathname === base
                : pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link key={item.href} href={href} className={active ? "active" : ""}>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <Link href="/" className="nav-back">
          All projects
        </Link>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
