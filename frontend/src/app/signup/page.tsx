"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ArrowRight, LockKeyhole, ShieldCheck } from "lucide-react";
import { Brand } from "@/components/brand";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { ThemeToggle } from "@/components/theme-provider";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/input";
import { ApiError, api, API_URL } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { AuthResponse } from "@/lib/types";
import { homeFor } from "@/hooks/use-session";

const BRANCHES = ["CSE", "IT", "ECE", "EEE", "MECH", "CIVIL", "AI & DS"];
const ROLES = [
  "Software Engineer",
  "Backend Engineer",
  "Data Analyst",
  "Data Scientist",
  "Product Manager",
  "Core Electronics",
  "VLSI Engineer",
];

export default function SignupPage() {
  const t = useTranslations("auth");
  const router = useRouter();
  const { user, ready, setSession } = useAuthStore();
  const [form, setForm] = useState({
    name: "",
    email: "",
    college_code: "NOVA",
    password: "",
    branch: "CSE",
    target_role: "Software Engineer",
  });
  const [consent, setConsent] = useState(false);
  const [share, setShare] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (ready && user) router.replace(homeFor(user.role));
  }, [ready, user, router]);

  function update<K extends keyof typeof form>(key: K, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (!consent) {
      setError(t("consentRequired"));
      return;
    }
    setLoading(true);
    try {
      const data = await api.post<AuthResponse>("/auth/register", {
        ...form,
        college_code: form.college_code.trim().toUpperCase(),
        consent_notice: true,
        share_analytics: share,
      });
      setSession(data.access_token, data.user);
      router.replace("/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("genericError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-[0.95fr_1.05fr]">
      <div className="flex flex-col px-4 py-6 sm:px-10 lg:px-14">
        <div className="flex items-center justify-between">
          <Brand />
          <div className="flex items-center gap-2">
            <LocaleSwitcher />
            <ThemeToggle />
          </div>
        </div>
        <div className="mx-auto w-full max-w-lg flex-1 py-10">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-primary">
            First win in under a minute
          </p>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight">
            {t("signupTitle")}
          </h1>
          <p className="mt-2 text-sm text-muted">{t("signupSubtitle")}</p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="name">{t("name")}</Label>
                <Input
                  id="name"
                  required
                  minLength={2}
                  autoComplete="name"
                  value={form.name}
                  onChange={(event) => update("name", event.target.value)}
                  placeholder="Aarav Sharma"
                />
              </div>
              <div>
                <Label htmlFor="college_code">{t("collegeCode")}</Label>
                <Input
                  id="college_code"
                  required
                  value={form.college_code}
                  onChange={(event) => update("college_code", event.target.value.toUpperCase())}
                  placeholder="NOVA"
                />
                <p className="mt-1 text-[10px] text-muted">{t("collegeCodeHint")}</p>
              </div>
            </div>
            <div>
              <Label htmlFor="email">{t("email")}</Label>
              <Input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={form.email}
                onChange={(event) => update("email", event.target.value)}
                placeholder="you@college.edu"
              />
            </div>
            <div>
              <Label htmlFor="password">{t("password")}</Label>
              <Input
                id="password"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={form.password}
                onChange={(event) => update("password", event.target.value)}
                placeholder="At least 8 characters"
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="branch">{t("branch")}</Label>
                <Select
                  id="branch"
                  value={form.branch}
                  onChange={(event) => update("branch", event.target.value)}
                >
                  {BRANCHES.map((branch) => (
                    <option key={branch} value={branch}>
                      {branch}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label htmlFor="target_role">{t("targetRole")}</Label>
                <Select
                  id="target_role"
                  value={form.target_role}
                  onChange={(event) => update("target_role", event.target.value)}
                >
                  {ROLES.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </Select>
              </div>
            </div>

            <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-primary">
                <ShieldCheck className="size-4" /> {t("privacyTitle")}
              </div>
              <p className="text-[11px] leading-relaxed text-muted">{t("privacyBody")}</p>
              <label className="mt-3 flex cursor-pointer items-start gap-2.5 text-xs text-fg">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                  className="mt-0.5 size-4 shrink-0 accent-[hsl(var(--primary))]"
                />
                <span>{t("consentNotice")}</span>
              </label>
              <div className="mt-3 flex items-start justify-between gap-3 border-t border-border/60 pt-3">
                <div>
                  <p className="text-xs font-semibold">{t("shareAnalytics")}</p>
                  <p className="text-[10px] text-muted">{t("shareHint")}</p>
                </div>
                <Switch checked={share} onCheckedChange={setShare} label={t("shareAnalytics")} />
              </div>
            </div>

            {error ? (
              <p
                role="alert"
                className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger"
              >
                {error}
              </p>
            ) : null}

            <Button type="submit" className="w-full" size="lg" loading={loading}>
              {loading ? t("creating") : t("signUp")} <ArrowRight />
            </Button>
          </form>

          <div className="mt-6 flex flex-col items-center gap-3 text-sm text-muted">
            <a
              href={`${API_URL}/auth/google/login?college_code=${encodeURIComponent(form.college_code || "NOVA")}`}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-xs font-semibold text-fg transition-colors hover:border-primary/40"
            >
              <span className="font-bold text-[#4285F4]">G</span> {t("google")}
            </a>
            <p>
              {t("haveAccount")}{" "}
              <Link href="/login" className="font-semibold text-accent hover:underline">
                {t("signIn")}
              </Link>
            </p>
          </div>
        </div>
      </div>

      <aside className="relative hidden overflow-hidden border-l border-border/60 bg-surface/40 lg:flex lg:flex-col lg:justify-center lg:px-14">
        <div className="pointer-events-none absolute inset-0 bg-brand-soft" />
        <div className="pointer-events-none absolute -left-20 bottom-10 size-80 rounded-full bg-accent/15 blur-[120px]" />
        <div className="relative max-w-md">
          <div className="glass w-fit rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-accent">
            Built for DPDP
          </div>
          <h2 className="mt-5 font-display text-3xl font-semibold leading-tight">
            Your data is yours. Full stop.
          </h2>
          <div className="mt-8 space-y-4">
            {[
              [
                "Consent at sign-up",
                "Analytics sharing is off by default. Turn it on or off any time.",
              ],
              [
                "Tenant isolation",
                "College A can never query College B's data — enforced at the repository layer.",
              ],
              [
                "Delete everything",
                "One endpoint removes your account, files, analyses, transcripts and scores.",
              ],
              [
                "No invented experience",
                "Every suggested resume edit is checked against the source evidence before it is shown.",
              ],
            ].map(([title, body]) => (
              <div key={title} className="flex gap-3">
                <LockKeyhole className="mt-0.5 size-4 shrink-0 text-primary" />
                <div>
                  <p className="text-xs font-semibold">{title}</p>
                  <p className="text-[11px] leading-relaxed text-muted">{body}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-8 text-[11px] text-muted">
            Demo college code: <span className="font-mono text-accent">NOVA</span>
          </p>
        </div>
      </aside>
    </div>
  );
}
