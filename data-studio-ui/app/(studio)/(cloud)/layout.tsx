import { OrgShell } from "@/components/org-shell";

export default function CloudLayout({ children }: { children: React.ReactNode }) {
  return <OrgShell>{children}</OrgShell>;
}
