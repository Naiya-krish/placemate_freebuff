"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  FileSearch,
  LockKeyhole,
  MessagesSquare,
  Sparkles,
  Target,
  Timer,
} from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { ReadinessRing } from "@/components/charts/readiness-ring";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const FEATURES = [
  {
    icon: FileSearch,
    titleKey: "feature1Title",
    bodyKey: "feature1Body",
    className: "md:col-span-4",
    accent: "from-violet-500/20 to-transparent",
  },
  {
    icon: MessagesSquare,
    titleKey: "feature2Title",
    bodyKey: "feature2Body",
    className: "md:col-span-4",
    accent: "from-cyan-400/20 to-transparent",
  },
  {
    icon: BarChart3,
    titleKey: "feature3Title",
    bodyKey: "feature3Body",
    className: "md:col-span-4",
    accent: "from-fuchsia-400/15 to-transparent",
  },
] as const;

export default function LandingPage() {
  const t = useTranslations("landing");
  return (
    <div className="min-h-dvh overflow-hidden">
      <SiteHeader />

      <section className="relative isolate px-4 pb-16 pt-14 md:px-6 md:pt-20">
        <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[620px] bg-brand-soft" />
        <div className="pointer-events-none absolute left-1/2 top-24 -z-10 size-[520px] -translate-x-1/2 rounded-full bg-primary/20 blur-[140px]" />
        <div className="mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="animate-rise">
            <Badge variant="accent" className="mb-5 gap-2 py-1">
              <Sparkles className="size-3" /> {t("badge")}
            </Badge>
            <h1 className="max-w-2xl text-balance font-display text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl md:text-6xl">
              {t("title").split(".")[0]}
              <span className="gradient-text">.</span>
            </h1>
            <p className="mt-5 max-w-xl text-pretty text-base leading-relaxed text-muted sm:text-lg">
              {t("subtitle")}
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <Button asChild size="lg">
                <Link href="/signup">
                  {t("primary")} <ArrowRight />
                </Link>
              </Button>
              <Button asChild size="lg" variant="secondary">
                <Link href="/login">{t("secondary")}</Link>
              </Button>
            </div>
            <div className="mt-5 flex items-center gap-2 text-xs text-muted">
              <LockKeyhole className="size-3.5 text-accent" /> {t("trust")}
            </div>

            <dl className="mt-10 grid max-w-lg grid-cols-3 gap-4">
              {[
                ["02:41", t("stat1")],
                ["3", t("stat2")],
                ["100%", t("stat3")],
              ].map(([value, label]) => (
                <div key={label}>
                  <dt className="font-display text-2xl font-semibold text-fg">{value}</dt>
                  <dd className="mt-1 text-[11px] leading-snug text-muted">{label}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="relative mx-auto w-full max-w-md lg:max-w-none">
            <div className="absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-br from-primary/25 via-transparent to-accent/20 blur-2xl" />
            <div className="surface-card brand-border relative overflow-hidden p-5">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">
                    {t("previewTitle")}
                  </p>
                  <p className="mt-1 text-sm font-semibold">Aarav Sharma · CSE</p>
                </div>
                <Badge variant="success">Interview-ready</Badge>
              </div>
              <div className="flex items-center gap-5 rounded-2xl border border-border/70 bg-surface/60 p-4">
                <ReadinessRing score={78} size={132} stroke={10} hint={t("previewSubtitle")} />
                <div className="flex-1 space-y-3">
                  {[
                    ["Technical depth", 84],
                    ["Problem solving", 76],
                    ["Clarity", 71],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <div className="mb-1 flex justify-between text-[10px] text-muted">
                        <span>{label}</span>
                        <span>{value}</span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-border/60">
                        <div
                          className="h-full rounded-full bg-brand-gradient"
                          style={{ width: `${value}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-border/70 bg-surface/50 p-3">
                  <p className="text-[10px] uppercase tracking-wide text-muted">Streak</p>
                  <p className="mt-1 font-display text-lg font-semibold">5 days 🔥</p>
                </div>
                <div className="rounded-xl border border-border/70 bg-surface/50 p-3">
                  <p className="text-[10px] uppercase tracking-wide text-muted">Next action</p>
                  <p className="mt-1 text-xs font-semibold text-accent">Practise technical depth</p>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2 rounded-xl border border-accent/20 bg-accent/5 px-3 py-2 text-[11px] text-accent">
                <Sparkles className="size-3.5" /> Grounded in your CampusRide project
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-7xl px-4 py-10 md:px-6 md:py-16">
        <div className="mb-8 flex items-end justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-primary">
              Built for the whole loop
            </p>
            <h2 className="mt-2 font-display text-2xl font-semibold sm:text-3xl">
              From resume to rubric, without the guesswork.
            </h2>
          </div>
          <Target className="hidden size-10 text-primary/40 md:block" />
        </div>
        <div className="grid gap-4 md:grid-cols-12">
          {FEATURES.map((feature) => {
            const Icon = feature.icon;
            return (
              <article
                key={feature.titleKey}
                className={`surface-card relative overflow-hidden p-6 md:col-span-4 ${feature.className}`}
              >
                <div
                  className={`pointer-events-none absolute -right-10 -top-10 size-40 rounded-full bg-gradient-to-br ${feature.accent} blur-2xl`}
                />
                <span className="mb-5 flex size-11 items-center justify-center rounded-2xl border border-border bg-surface text-primary">
                  <Icon className="size-5" aria-hidden />
                </span>
                <h3 className="text-base font-semibold">{t(feature.titleKey)}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{t(feature.bodyKey)}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section id="how" className="mx-auto max-w-7xl px-4 py-12 md:px-6">
        <div className="surface-card grid gap-6 p-6 md:grid-cols-3 md:p-8">
          {[
            {
              icon: FileSearch,
              step: "01",
              title: "Upload a resume",
              body: "PDF or DOCX, 5 MB max. Parsed with OCR fallback and strict validation.",
            },
            {
              icon: Timer,
              step: "02",
              title: "Get scored in < 60s",
              body: "Five subscores, tailored edits and missing-evidence flags. You accept or reject every change.",
            },
            {
              icon: MessagesSquare,
              step: "03",
              title: "Rehearse for real",
              body: "Three rounds, resume-grounded follow-ups, a visible rubric and median-scored feedback.",
            },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.step} className="relative">
                <span className="font-display text-5xl font-semibold text-primary/15">
                  {item.step}
                </span>
                <Icon className="mt-2 size-5 text-accent" aria-hidden />
                <h3 className="mt-3 text-sm font-semibold">{item.title}</h3>
                <p className="mt-1.5 text-xs leading-relaxed text-muted">{item.body}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section id="privacy" className="mx-auto max-w-7xl px-4 pb-20 md:px-6">
        <div className="surface-card flex flex-col items-start justify-between gap-6 overflow-hidden p-6 md:flex-row md:items-center md:p-10">
          <div className="max-w-xl">
            <Badge variant="muted" className="mb-3">
              Privacy by default
            </Badge>
            <h2 className="font-display text-2xl font-semibold">
              Your transcript is not your placement cell&apos;s dashboard.
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              Officers see aggregate heatmaps and readiness funnels. Individual readiness requires
              your explicit opt-in, and you can revoke it or delete your account at any time.
            </p>
          </div>
          <ul className="space-y-2 text-sm">
            {[
              "DPDP-aligned consent ledger",
              "No raw audio collected in Phase 1",
              "Sequential-tenant isolation enforced in the data layer",
            ].map((item) => (
              <li key={item} className="flex items-start gap-2 text-muted">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" /> {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <footer className="border-t border-border/60 px-4 py-8 md:px-6">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 text-xs text-muted sm:flex-row">
          <p>© {new Date().getFullYear()} PlaceMate. Built for placement season.</p>
          <div className="flex items-center gap-4">
            <Link href="/login" className="hover:text-fg">
              Sign in
            </Link>
            <a href="/manifest.webmanifest" className="hover:text-fg">
              Install app
            </a>
            <span className="text-muted/60">Phase 1 · text interviews</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
