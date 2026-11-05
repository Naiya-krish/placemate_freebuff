"use client";

import { AppShell, FullPageLoader } from "@/components/app-shell";
import { useRequireAuth } from "@/hooks/use-session";

export default function OfficerLayout({ children }: { children: React.ReactNode }) {
  const { user, ready } = useRequireAuth(["officer", "admin"]);
  if (!ready || !user) return <FullPageLoader label="Opening cohort analytics" />;
  return <AppShell user={user}>{children}</AppShell>;
}
