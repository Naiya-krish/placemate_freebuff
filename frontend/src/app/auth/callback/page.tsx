"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BrandMark } from "@/components/brand";
import { fetchCurrentUser, refreshSession } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { homeFor } from "@/hooks/use-session";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const refreshed = await refreshSession();
      if (!refreshed) {
        if (!cancelled) setFailed(true);
        return;
      }
      const user = await fetchCurrentUser();
      if (cancelled) return;
      if (!user) {
        setFailed(true);
        return;
      }
      useAuthStore.getState().setUser(user);
      router.replace(user.onboarding_complete ? homeFor(user.role) : "/onboarding");
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-bg px-6 text-center">
      <BrandMark className="size-12" />
      {failed ? (
        <>
          <h1 className="font-display text-xl font-semibold">Sign-in could not complete</h1>
          <p className="max-w-sm text-sm text-muted">
            The Google session expired or the callback failed. Please try again.
          </p>
          <a
            href="/login"
            className="mt-2 rounded-xl bg-brand-gradient px-4 py-2 text-sm font-semibold text-white"
          >
            Back to sign in
          </a>
        </>
      ) : (
        <>
          <h1 className="font-display text-xl font-semibold">Signing you in…</h1>
          <p className="text-sm text-muted">Verifying your college session.</p>
        </>
      )}
    </div>
  );
}
