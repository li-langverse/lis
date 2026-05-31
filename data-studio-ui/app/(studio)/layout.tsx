"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { STUDIO_NAV } from "@/lib/studio-nav";

export default function StudioLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">Li Data Studio</div>
        <div className="brand-sub">lis + lidb</div>
        <nav className="nav" aria-label="Studio">
          {STUDIO_NAV.map((item) => {
            const active =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link key={item.href} href={item.href} className={active ? "active" : ""}>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
