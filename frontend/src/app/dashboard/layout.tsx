"use client";

import { AppShell, FullPageLoader } from "@/components/app-shell";
import { useRequireAuth } from "@/hooks/use-session";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, ready } = useRequireAuth(["student"]);
  if (!ready || !user) return <FullPageLoader label="Opening your dashboard" />;
  return <AppShell user={user}>{children}</AppShell>;
}
