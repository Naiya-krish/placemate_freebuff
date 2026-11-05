"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  MessageSquareQuote,
  RefreshCw,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { BrandMark } from "@/components/brand";
import { ErrorState } from "@/components/app-shell";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { ThemeToggle } from "@/components/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/hooks/use-session";
import type { Feedback } from "@/lib/types";
import { cn, roundLabel, scoreTone } from "@/lib/utils";

function answerSignal(content: string): "strong" | "thin" | "neutral" {
  const words = content.trim().split(/\s+/).length;
  const concrete =
    /\b\d+(?:\.\d+)?%|\b(trade-?off|because|measured|tested|result|latency|reduced|improved)\b/i.test(
      content,
    );
  if (words >= 45 && concrete) return "strong";
  if (words < 25) return "thin";
  return "neutral";
}

export default function FeedbackPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const t = useTranslations("feedback");
  const ti = useTranslations("interviews");
  const { ready } = useRequireAuth(["student"]);

  const feedbackQuery = useQuery<Feedback>({
    queryKey: ["feedback", id],
    queryFn: () => api.get<Feedback>(`/interviews/${id}/feedback`),
    retry: false,
  });

  const data = feedbackQuery.data;
  const overall = data?.overall_score ? Math.round(data.overall_score) : 0;

  if (!ready) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg text-sm text-muted">
        Loading…
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-bg">
      <header className="sticky top-0 z-30 border-b border-border/70 bg-bg/85 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 md:px-6">
          <div className="flex items-center gap-2.5">
            <BrandMark className="size-8" />
            <div>
              <p className="text-xs font-semibold">{t("title")}</p>
              <p className="text-[10px] text-muted">
                {data ? `Rubric ${data.rubric_version}` : ti("rubricVersion", { version: "…" })}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <LocaleSwitcher className="hidden sm:flex" />
            <ThemeToggle />
            <Button asChild variant="ghost" size="sm">
              <Link href="/dashboard">
                <ArrowLeft /> <span className="hidden sm:inline">{t("back")}</span>
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 md:px-6">
        {feedbackQuery.isLoading ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <Skeleton className="h-[560px] w-full" />
            <Skeleton className="h-[560px] w-full" />
          </div>
        ) : feedbackQuery.isError || !data ? (
          <div className="mx-auto max-w-md py-20">
            <ErrorState
              message="Feedback is not available yet. Finish the interview to unlock it."
              onRetry={() => feedbackQuery.refetch()}
            />
            <div className="mt-4 flex justify-center gap-2">
              <Button asChild variant="secondary">
                <Link href={`/interview/${id}`}>{ti("continue")}</Link>
              </Button>
              <Button asChild>
                <Link href="/dashboard/interviews">{ti("title")}</Link>
              </Button>
            </div>
          </div>
        ) : (
          <>
            <div className="mb-5 flex flex-col gap-4 rounded-2xl border border-border bg-surface/40 p-5 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-4">
                <div className="flex size-20 flex-col items-center justify-center rounded-2xl border border-primary/20 bg-primary/5">
                  <span className={cn("font-display text-3xl font-semibold", scoreTone(overall))}>
                    {overall}
                  </span>
                  <span className="text-[9px] uppercase tracking-wide text-muted">/ 100</span>
                </div>
                <div>
                  <h1 className="font-display text-xl font-semibold">{t("title")}</h1>
                  <p className="mt-1 max-w-2xl text-sm text-muted">
                    {data.feedback.summary ?? t("noFeedback")}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <Badge variant="muted">
                      {t("samples", {
                        count: data.feedback.samples_used ?? 3,
                        version: data.rubric_version,
                      })}
                    </Badge>
                    {data.variance_flag ? (
                      <Badge variant="warning">
                        <AlertTriangle className="size-3" /> {t("variance")}
                      </Badge>
                    ) : (
                      <Badge variant="success">
                        <CheckCircle2 className="size-3" /> stable samples
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button asChild variant="secondary">
                  <Link href="/dashboard/interviews">
                    <RefreshCw /> {t("retry")}
                  </Link>
                </Button>
                <Button asChild>
                  <Link href="/dashboard">
                    {t("back")} <ArrowRight />
                  </Link>
                </Button>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="flex max-h-[calc(100dvh-14rem)] flex-col">
                <CardHeader>
                  <div>
                    <CardTitle>{t("transcript")}</CardTitle>
                    <CardDescription>
                      Strong answers are highlighted; thin answers need evidence.
                    </CardDescription>
                  </div>
                  <MessageSquareQuote className="size-4 text-muted" />
                </CardHeader>
                <CardContent className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
                  {data.transcript.map((turn) => {
                    if (turn.speaker === "system") return null;
                    const signal =
                      turn.speaker === "candidate" ? answerSignal(turn.content) : "neutral";
                    return (
                      <div
                        key={turn.id}
                        className={cn(
                          "rounded-2xl border p-3.5",
                          turn.speaker === "interviewer"
                            ? "border-border bg-surface/50"
                            : signal === "strong"
                              ? "border-success/25 bg-success/5"
                              : signal === "thin"
                                ? "border-warning/25 bg-warning/5"
                                : "border-border bg-surface/35",
                        )}
                      >
                        <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                          <span className="text-[9px] font-semibold uppercase tracking-wider text-muted">
                            {turn.speaker === "interviewer"
                              ? `Interviewer · ${roundLabel(turn.round)}`
                              : "You"}
                          </span>
                          {turn.is_followup ? (
                            <Badge variant="default" className="px-1.5 py-0 text-[8px]">
                              follow-up
                            </Badge>
                          ) : null}
                          {turn.speaker === "candidate" && signal !== "neutral" ? (
                            <Badge
                              variant={signal === "strong" ? "success" : "warning"}
                              className="px-1.5 py-0 text-[8px]"
                            >
                              {signal === "strong" ? "Strong signal" : "Needs evidence"}
                            </Badge>
                          ) : null}
                        </div>
                        <p className="text-xs leading-relaxed">{turn.content}</p>
                      </div>
                    );
                  })}
                </CardContent>
              </Card>

              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <div>
                      <CardTitle>{t("rubric")}</CardTitle>
                      <CardDescription>Median of three samples · weighted overall</CardDescription>
                    </div>
                    <TrendingUp className="size-4 text-primary" />
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {data.criteria.map((criterion) => (
                      <div
                        key={criterion.key}
                        className="rounded-xl border border-border bg-surface/35 p-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-xs font-semibold">{criterion.label}</p>
                          <div className="flex items-center gap-2">
                            <span
                              className={cn(
                                "font-display text-sm font-semibold",
                                scoreTone(criterion.score * 10),
                              )}
                            >
                              {criterion.score}/10
                            </span>
                            <Badge variant="muted" className="px-1.5 py-0 text-[8px]">
                              {Math.round(criterion.weight * 100)}%
                            </Badge>
                          </div>
                        </div>
                        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-border/60">
                          <div
                            className="h-full rounded-full bg-brand-gradient"
                            style={{ width: `${criterion.score * 10}%` }}
                          />
                        </div>
                        <p className="mt-2 text-[11px] leading-relaxed text-muted">
                          {criterion.note}
                        </p>
                        <p className="mt-2 rounded-lg border border-accent/15 bg-accent/5 px-2.5 py-1.5 text-[10px] leading-relaxed text-accent">
                          <Sparkles className="mr-1 inline size-3" />
                          {criterion.improvement}
                        </p>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">{t("strong")}</CardTitle>
                      <CheckCircle2 className="size-4 text-success" />
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {(data.feedback.strengths ?? []).map((item) => (
                          <li
                            key={item}
                            className="flex gap-2 text-[11px] leading-relaxed text-muted"
                          >
                            <span className="mt-1 size-1.5 shrink-0 rounded-full bg-success" />
                            {item}
                          </li>
                        ))}
                        {(data.feedback.strengths ?? []).length === 0 ? (
                          <li className="text-[11px] text-muted">{t("noFeedback")}</li>
                        ) : null}
                      </ul>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">{t("improve")}</CardTitle>
                      <TrendingUp className="size-4 text-primary" />
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {(data.feedback.improvements ?? []).map((item) => (
                          <li
                            key={item}
                            className="flex gap-2 text-[11px] leading-relaxed text-muted"
                          >
                            <span className="mt-1 size-1.5 shrink-0 rounded-full bg-primary" />
                            {item}
                          </li>
                        ))}
                        {(data.feedback.improvements ?? []).length === 0 ? (
                          <li className="text-[11px] text-muted">{t("noFeedback")}</li>
                        ) : null}
                      </ul>
                    </CardContent>
                  </Card>
                </div>

                <p className="text-center text-[10px] text-muted">
                  {data.variance_flag ? t("variance") : "Scores are reproducible and versioned."}
                </p>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
