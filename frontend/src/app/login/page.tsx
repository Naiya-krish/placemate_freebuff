"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ArrowRight, BriefcaseBusiness, GraduationCap, ShieldCheck, Sparkles } from "lucide-react";
import { Brand } from "@/components/brand";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { ThemeToggle } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { ApiError, DEMO_MODE, demoLogin, login } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { homeFor } from "@/hooks/use-session";

const DEMO_ROLES = [
  { role: "student" as const, labelKey: "demoStudent", icon: GraduationCap },
  { role: "officer" as const, labelKey: "demoOfficer", icon: BriefcaseBusiness },
  { role: "admin" as const, labelKey: "demoAdmin", icon: ShieldCheck },
];

export default function LoginPage() {
  const t = useTranslations("auth");
  const router = useRouter();
  const { user, ready, setSession } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState<string | null>(null);

  useEffect(() => {
    if (ready && user) router.replace(homeFor(user.role));
  }, [ready, user, router]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await login(email.trim(), password);
      setSession(data.access_token, data.user);
      router.replace(data.user.onboarding_complete ? homeFor(data.user.role) : "/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("genericError"));
    } finally {
      setLoading(false);
    }
  }

  async function demo(role: "student" | "officer" | "admin") {
    setError(null);
    setDemoLoading(role);
    try {
      const data = await demoLogin(role);
      setSession(data.access_token, data.user);
      router.replace(homeFor(data.user.role));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("genericError"));
    } finally {
      setDemoLoading(null);
    }
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.05fr_0.95fr]">
      <div className="flex flex-col px-4 py-6 sm:px-10 lg:px-16">
        <div className="flex items-center justify-between">
          <Brand />
          <div className="flex items-center gap-2">
            <LocaleSwitcher />
            <ThemeToggle />
          </div>
        </div>
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-12">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-primary">
            {t("welcomeBack")}
          </p>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight">{t("signIn")}</h1>
          <p className="mt-2 text-sm text-muted">{t("loginSubtitle")}</p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            <div>
              <Label htmlFor="email">{t("email")}</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@college.edu"
              />
            </div>
            <div>
              <Label htmlFor="password">{t("password")}</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
              />
            </div>
            {error ? (
              <p
                role="alert"
                className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger"
              >
                {error}
              </p>
            ) : null}
            <Button
              type="submit"
              className="w-full"
              loading={loading}
              disabled={demoLoading !== null}
            >
              {loading ? t("signingIn") : t("signIn")} <ArrowRight />
            </Button>
          </form>

          {DEMO_MODE ? (
            <div className="mt-7 rounded-2xl border border-border bg-surface/60 p-4">
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold">
                <Sparkles className="size-3.5 text-accent" /> {t("demoTitle")}
              </div>
              <div className="grid gap-2 sm:grid-cols-3">
                {DEMO_ROLES.map(({ role, labelKey, icon: Icon }) => (
                  <Button
                    key={role}
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="justify-start text-[11px]"
                    onClick={() => demo(role)}
                    loading={demoLoading === role}
                    disabled={loading || (demoLoading !== null && demoLoading !== role)}
                  >
                    <Icon /> {t(labelKey)}
                  </Button>
                ))}
              </div>
              <p className="mt-3 text-[10px] leading-relaxed text-muted">{t("demoHint")}</p>
            </div>
          ) : null}

          <p className="mt-7 text-center text-sm text-muted">
            {t("noAccount")}{" "}
            <Link href="/signup" className="font-semibold text-accent hover:underline">
              {t("signUp")}
            </Link>
          </p>
        </div>
      </div>

      <aside className="relative hidden overflow-hidden border-l border-border/60 bg-surface/40 lg:flex lg:flex-col lg:justify-center lg:px-14">
        <div className="pointer-events-none absolute inset-0 bg-brand-soft" />
        <div className="pointer-events-none absolute -right-24 top-1/4 size-80 rounded-full bg-primary/25 blur-[120px]" />
        <div className="relative">
          <div className="glass w-fit rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-accent">
            Visible rubric · median of 3 samples
          </div>
          <h2 className="mt-5 max-w-md font-display text-3xl font-semibold leading-tight">
            Practice the interview you are actually going to get.
          </h2>
          <div className="mt-8 space-y-3">
            {[
              ["Clarity", 18, "structured, concise answers"],
              ["Technical depth", 24, "mechanisms and trade-offs"],
              ["Problem solving", 22, "validate the outcome"],
              ["Communication", 16, "answer the question asked"],
              ["Role fit", 20, "evidence for this role"],
            ].map(([label, weight, description]) => (
              <div
                key={String(label)}
                className="flex items-center justify-between gap-4 rounded-xl border border-border/70 bg-card/60 px-4 py-3"
              >
                <div>
                  <p className="text-xs font-semibold">{label}</p>
                  <p className="text-[10px] text-muted">{description}</p>
                </div>
                <span className="font-display text-sm tabular-nums text-primary">{weight}%</span>
              </div>
            ))}
          </div>
          <p className="mt-6 max-w-sm text-xs leading-relaxed text-muted">
            Scores are stored with their rubric version, prompt version and model. If the three
            samples disagree, the interview is flagged for human review.
          </p>
        </div>
      </aside>
    </div>
  );
}
