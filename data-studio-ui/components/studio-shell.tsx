"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { CommandPalette } from "@/components/command-palette";
import { STUDIO_NAV } from "@/lib/studio-nav";

export function StudioShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [paletteOpen, setPaletteOpen] = useState(false);

  const onRefresh = useCallback(() => {
    router.refresh();
  }, [router]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const navItems = [{ href: "/", label: "Home" }, ...STUDIO_NAV, { href: "/agents", label: "Agents" }];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">Li Data Studio</div>
        <div className="brand-sub">lis + lidb · beat Supabase</div>
        <button type="button" className="palette-trigger" onClick={() => setPaletteOpen(true)}>
          <span>Search…</span>
          <kbd className="kbd-hint">⌘K</kbd>
        </button>
        <nav className="nav" aria-label="Studio">
          {navItems.map((item) => {
            const active =
              pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link key={item.href} href={item.href} className={active ? "active" : ""}>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="content">{children}</main>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} onRefresh={onRefresh} />
    </div>
  );
}
