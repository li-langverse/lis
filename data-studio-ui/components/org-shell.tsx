"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Props = {
  children: React.ReactNode;
};

export function OrgShell({ children }: Props) {
  const pathname = usePathname();

  return (
    <div className="app-shell org-shell">
      <aside className="sidebar">
        <div className="brand">Li Data Studio</div>
        <div className="brand-sub">Cloud console for lidb projects</div>
        <nav className="nav" aria-label="Organization">
          <Link href="/" className={pathname === "/" ? "active" : ""}>
            Projects
          </Link>
          <Link href="/agents" className={pathname === "/agents" ? "active" : ""}>
            Agents
          </Link>
        </nav>
        <div className="sidebar-footer">
          <button type="button" className="btn btn-ghost" disabled title="OAuth sign-in planned (C1)">
            Sign in
          </button>
        </div>
      </aside>
      <main className="content content-wide">{children}</main>
    </div>
  );
}
