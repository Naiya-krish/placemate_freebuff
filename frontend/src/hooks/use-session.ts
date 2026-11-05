"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, fetchCurrentUser, refreshSession } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { Role, User } from "@/lib/types";

export function useSessionBootstrap() {
  const { setUser, setReady, ready } = useAuthStore();

  useEffect(() => {
    if (ready) return;
    let cancelled = false;
    (async () => {
      const state = useAuthStore.getState();
      if (state.accessToken) {
        const user = await fetchCurrentUser();
        if (!cancelled) {
          if (user) setUser(user);
          else state.clear();
          setReady(true);
        }
        return;
      }
      const refreshed = await refreshSession();
      if (cancelled) return;
      if (refreshed) {
        const user = await fetchCurrentUser();
        if (user && !cancelled) setUser(user);
      }
      setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [ready, setReady, setUser]);
}

const roleHome: Record<Role, string> = {
  student: "/dashboard",
  officer: "/officer",
  admin: "/admin",
};

export function useRequireAuth(roles?: Role[]): { user: User | null; ready: boolean } {
  const router = useRouter();
  const pathname = usePathname();
  const { user, ready } = useAuthStore();

  useEffect(() => {
    if (!ready) return;
    if (!user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    if (roles && !roles.includes(user.role)) {
      router.replace(roleHome[user.role]);
    }
  }, [ready, user, roles, router, pathname]);

  return { user, ready };
}

export function homeFor(role: Role | undefined): string {
  if (!role) return "/login";
  return roleHome[role];
}

export { api };
