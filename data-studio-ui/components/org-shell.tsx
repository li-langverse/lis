"use client";

import Link from "next/link";

type Props = {
  children: React.ReactNode;
};

export function OrgShell({ children }: Props) {
  return (
    <div className="app-shell org-shell">
      <aside className="sidebar">
        <div className="brand">Librebase</div>
        <div className="brand-sub">Projects, studio, and agents on lidb</div>
        <nav className="nav" aria-label="Organization">
          <Link href="/" className="active">
            Projects
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
