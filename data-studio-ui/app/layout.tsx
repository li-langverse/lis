import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Li Data Studio",
  description: "Console for lidb and lis db — Supabase Studio–aligned UI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
