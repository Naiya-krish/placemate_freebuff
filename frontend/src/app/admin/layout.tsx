"use client";

import { AppShell, FullPageLoader } from "@/components/app-shell";
import { useRequireAuth } from "@/hooks/use-session";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, ready } = useRequireAuth(["admin"]);
  if (!ready || !user) return <FullPageLoader label="Opening admin console" />;
  return <AppShell user={user}>{children}</AppShell>;
}
