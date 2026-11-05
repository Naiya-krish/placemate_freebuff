"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  ArrowRight,
  Award,
  CalendarDays,
  FileSearch,
  FileText,
  Flame,
  Mic,
  ShieldCheck,
  Sparkles,
  Target,
  Trophy,
  UploadCloud,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ErrorState, PageHeading } from "@/components/app-shell";
import { ReadinessRing } from "@/components/charts/readiness-ring";
import { SkillRadar } from "@/components/charts/skill-radar";
import { Confetti } from "@/components/confetti";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DashboardSkeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { Dashboard, Usage } from "@/lib/types";
import { cn, formatCurrency, formatRelative, readinessBand, scoreTone } from "@/lib/utils";

const BADGE_ICONS: Record<string, LucideIcon> = {
  file: FileText,
  mic: Mic,
  trophy: Trophy,
  sparkles: Sparkles,
  flame: Flame,
  shield: ShieldCheck,
  zap: Zap,
};

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const user = useAuthStore((state) => state.user);
  const [fire, setFire] = useState(false);

  const dashboardQuery = useQuery<Dashboard>({
    queryKey: ["dashboard"],
    queryFn: () => api.get<Dashboard>("/dashboard/student"),
  });
  const usageQuery = useQuery<Usage>({
    queryKey: ["usage"],
    queryFn: () => api.get<Usage>("/usage/me"),
    retry: false,
  });

  const data = dashboardQuery.data;

  useEffect(() => {
    if (!data || (!data.has_interview && data.resume_score === null)) return;
    try {
      if (localStorage.getItem("placemate-celebrated-v1")) return;
      localStorage.setItem("placemate-celebrated-v1", "1");
      setFire(true);
      const timer = setTimeout(() => setFire(false), 2800);
      return () => clearTimeout(timer);
    } catch {
      return;
    }
  }, [data]);

  if (dashboardQuery.isLoading) {
    return (
      <>
        <PageHeading
          title={t("greeting", { name: user?.name.split(" ")[0] ?? "there" })}
          subtitle={t("focus")}
        />
        <DashboardSkeleton />
      </>
    );
  }

  if (dashboardQuery.isError || !data) {
    return (
      <>
        <PageHeading title="Dashboard" subtitle={t("focus")} />
        <ErrorState
          message="We could not load your dashboard."
          onRetry={() => dashboardQuery.refetch()}
        />
      </>
    );
  }

  const band = readinessBand(data.readiness);
  const earned = data.badges.filter((badge) => badge.earned);

  return (
    <>
      <Confetti fire={fire} />
      <PageHeading
        eyebrow={band.label}
        title={t("greeting", { name: user?.name.split(" ")[0] ?? "there" })}
        subtitle={t("focus")}
        actions={
          <Button asChild>
            <Link href={data.has_resume ? "/dashboard/interviews" : "/dashboard/resume"}>
              {data.has_resume ? t("startInterview") : "Upload resume"} <ArrowRight />
            </Link>
          </Button>
        }
      />

      {!data.has_resume ? (
        <div className="surface-card brand-border mb-4 flex flex-col items-start gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <span className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <UploadCloud className="size-5" />
            </span>
            <div>
              <h2 className="text-sm font-semibold">{t("emptyTitle")}</h2>
              <p className="mt-1 max-w-lg text-xs leading-relaxed text-muted">{t("emptyBody")}</p>
            </div>
          </div>
          <Button asChild size="sm">
            <Link href="/dashboard/resume">Upload resume</Link>
          </Button>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-6 xl:grid-cols-12">
        <Card className="relative overflow-hidden md:col-span-4 xl:col-span-4">
          <div className="pointer-events-none absolute -right-16 -top-20 size-56 rounded-full bg-primary/15 blur-3xl" />
          <CardHeader>
            <div>
              <CardTitle>{t("readiness")}</CardTitle>
              <CardDescription>{t("readinessHint")}</CardDescription>
            </div>
            <Badge variant={data.readiness >= 70 ? "success" : "default"}>{band.label}</Badge>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4">
            <ReadinessRing score={data.readiness} size={190} stroke={13} />
            <div className="grid w-full grid-cols-3 gap-2 text-center">
              <div className="rounded-xl border border-border/60 bg-surface/60 p-2.5">
                <p className="text-[10px] uppercase tracking-wide text-muted">{t("resumeScore")}</p>
                <p
                  className={cn(
                    "mt-1 font-display text-lg font-semibold",
                    scoreTone(data.resume_score ?? 0),
                  )}
                >
                  {data.resume_score ?? "—"}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-surface/60 p-2.5">
                <p className="text-[10px] uppercase tracking-wide text-muted">
                  {t("interviewScore")}
                </p>
                <p
                  className={cn(
                    "mt-1 font-display text-lg font-semibold",
                    scoreTone(data.interview_score ?? 0),
                  )}
                >
                  {data.interview_score ?? "—"}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-surface/60 p-2.5">
                <p className="text-[10px] uppercase tracking-wide text-muted">{t("size")}</p>
                <p className="mt-1 font-display text-lg font-semibold">
                  {data.completed_interviews}
                </p>
              </div>
            </div>
            <div className="flex w-full items-center justify-between rounded-xl border border-border/60 bg-surface/40 px-3 py-2 text-[11px]">
              <span className="flex items-center gap-1.5 text-muted">
                <CalendarDays className="size-3.5" /> {t("placementIn")}
              </span>
              <span className="font-semibold text-fg">
                {data.days_to_placement !== null
                  ? t("daysLeft", { count: data.days_to_placement })
                  : "—"}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-primary/20 md:col-span-2 xl:col-span-5">
          <div className="pointer-events-none absolute inset-0 bg-brand-soft opacity-70" />
          <div className="relative">
            <CardHeader>
              <div>
                <Badge variant="accent" className="mb-2">
                  <Target className="size-3" /> {t("nextBestAction")}
                </Badge>
                <CardTitle className="text-lg leading-snug">{data.next_action.title}</CardTitle>
                <CardDescription className="mt-1.5 text-sm leading-relaxed">
                  {data.next_action.description}
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Button asChild>
                  <Link href={data.next_action.href}>
                    {data.next_action.cta} <ArrowRight />
                  </Link>
                </Button>
                <Button asChild variant="secondary">
                  <Link href="/dashboard/interviews">See rubric</Link>
                </Button>
              </div>
              {data.skill_gaps.length ? (
                <div className="mt-5">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">
                    {t("skillGaps")}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {data.skill_gaps.map((gap) => (
                      <Badge key={gap} variant="muted">
                        {gap}
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </div>
        </Card>

        <Card className="md:col-span-2 xl:col-span-3">
          <CardHeader>
            <div>
              <CardTitle>{t("streak")}</CardTitle>
              <CardDescription>{t("level", { level: data.level })}</CardDescription>
            </div>
            <span className="flex size-9 items-center justify-center rounded-xl bg-warning/10 text-warning">
              <Flame className="size-5" />
            </span>
          </CardHeader>
          <CardContent>
            <p className="font-display text-3xl font-semibold">
              {data.streak}
              <span className="ml-1.5 text-xs font-medium text-muted">
                {t("days", { count: data.streak })}
              </span>
            </p>
            <div className="mt-4 flex items-center justify-between text-[10px] text-muted">
              <span className="flex items-center gap-1">
                <Zap className="size-3 text-primary" /> {data.xp} {t("xp")}
              </span>
              <span>{data.level_progress}%</span>
            </div>
            <Progress value={data.level_progress} className="mt-1.5 h-1.5" />
            <p className="mt-2 text-[10px] text-muted">
              {t("nextLevel", {
                points: 250 - Math.round((data.level_progress / 100) * 250),
                level: data.level + 1,
              })}
            </p>
          </CardContent>
        </Card>

        <Card className="md:col-span-3 xl:col-span-4">
          <CardHeader>
            <div>
              <CardTitle>{t("skillRadar")}</CardTitle>
              <CardDescription>{t("radarHint")}</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            {data.radar.some((point) => point.value > 0) ? (
              <SkillRadar data={data.radar} />
            ) : (
              <p className="py-14 text-center text-sm text-muted">{t("emptyBody")}</p>
            )}
          </CardContent>
        </Card>

        <Card className="md:col-span-3 xl:col-span-4">
          <CardHeader>
            <div>
              <CardTitle>{t("badges")}</CardTitle>
              <CardDescription>{t("badgesHint")}</CardDescription>
            </div>
            <Award className="size-4 text-muted" />
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-2">
              {data.badges.map((badge) => {
                const Icon = BADGE_ICONS[badge.icon] ?? Award;
                return (
                  <div
                    key={badge.key}
                    title={badge.description}
                    className={cn(
                      "flex items-center gap-2.5 rounded-xl border p-2.5 transition-colors",
                      badge.earned
                        ? "border-primary/25 bg-primary/5"
                        : "border-border/60 bg-surface/30 opacity-55",
                    )}
                  >
                    <span
                      className={cn(
                        "flex size-8 shrink-0 items-center justify-center rounded-lg",
                        badge.earned ? "bg-primary/15 text-primary" : "bg-surface text-muted",
                      )}
                    >
                      <Icon className="size-4" />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-[11px] font-semibold">{badge.label}</p>
                      <p className="truncate text-[9px] text-muted">{badge.description}</p>
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="mt-3 text-[10px] text-muted">
              {earned.length} / {data.badges.length} unlocked
            </p>
          </CardContent>
        </Card>

        <Card className="md:col-span-4 xl:col-span-5">
          <CardHeader>
            <div>
              <CardTitle>{t("history")}</CardTitle>
              <CardDescription>Interviews and resume analyses</CardDescription>
            </div>
            <FileSearch className="size-4 text-muted" />
          </CardHeader>
          <CardContent>
            {data.history.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted">{t("emptyHistory")}</p>
            ) : (
              <ul className="divide-y divide-border/60">
                {data.history.slice(0, 6).map((item) => (
                  <li key={item.id} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="flex min-w-0 items-center gap-3">
                      <span
                        className={cn(
                          "flex size-8 shrink-0 items-center justify-center rounded-lg",
                          item.kind === "interview"
                            ? "bg-primary/10 text-primary"
                            : "bg-accent/10 text-accent",
                        )}
                      >
                        {item.kind === "interview" ? (
                          <Mic className="size-4" />
                        ) : (
                          <FileText className="size-4" />
                        )}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-xs font-semibold">{item.title}</p>
                        <p className="truncate text-[10px] text-muted">
                          {formatRelative(item.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {item.score !== null ? (
                        <span
                          className={cn(
                            "font-display text-sm font-semibold",
                            scoreTone(item.score),
                          )}
                        >
                          {item.score}
                        </span>
                      ) : null}
                      {item.kind === "interview" ? (
                        <Link
                          href={`/interview/${item.id}/feedback`}
                          className="rounded-lg border border-border px-2 py-1 text-[10px] font-semibold text-muted hover:text-fg"
                        >
                          View
                        </Link>
                      ) : (
                        <Link
                          href="/dashboard/resume"
                          className="rounded-lg border border-border px-2 py-1 text-[10px] font-semibold text-muted hover:text-fg"
                        >
                          Open
                        </Link>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="md:col-span-2 xl:col-span-3">
          <CardHeader>
            <div>
              <CardTitle>{t("usage")}</CardTitle>
              <CardDescription>{usageQuery.data?.month ?? "—"}</CardDescription>
            </div>
            <Sparkles className="size-4 text-accent" />
          </CardHeader>
          <CardContent>
            {usageQuery.data ? (
              <>
                <p className="font-display text-2xl font-semibold">
                  {usageQuery.data.percent_used}%
                </p>
                <Progress value={usageQuery.data.percent_used} className="mt-2 h-1.5" />
                <p className="mt-2 text-[10px] text-muted">
                  {t("budgetLeft", { amount: formatCurrency(usageQuery.data.remaining_usd) })}
                </p>
                <Link
                  href="/dashboard/settings"
                  className="mt-3 inline-flex items-center gap-1 text-[10px] font-semibold text-accent hover:underline"
                >
                  Budget details <ArrowRight className="size-3" />
                </Link>
              </>
            ) : (
              <p className="py-6 text-center text-xs text-muted">Usage unavailable</p>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
