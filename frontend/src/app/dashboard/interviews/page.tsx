"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Clock,
  FileText,
  LockKeyhole,
  MessagesSquare,
  Play,
  Plus,
  ShieldCheck,
} from "lucide-react";
import { ErrorState, PageHeading } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Label, Select } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { Interview, Resume, Rubric } from "@/lib/types";
import { cn, formatDuration, formatRelative, roleLabel, roundLabel, scoreTone } from "@/lib/utils";

const ROLE_OPTIONS = [
  { value: "swe", label: "Software engineering" },
  { value: "data", label: "Data & AI" },
  { value: "product", label: "Product" },
  { value: "core", label: "Core engineering" },
];

export default function InterviewsPage() {
  const t = useTranslations("interviews");
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const [open, setOpen] = useState(false);
  const [resumeId, setResumeId] = useState("");
  const [role, setRole] = useState("swe");
  const [error, setError] = useState<string | null>(null);

  const resumesQuery = useQuery<Resume[]>({
    queryKey: ["resumes"],
    queryFn: () => api.get<Resume[]>("/resumes"),
  });
  const rubricQuery = useQuery<Rubric>({
    queryKey: ["rubric"],
    queryFn: () => api.get<Rubric>("/rubrics/active"),
  });
  const interviewsQuery = useQuery<Interview[]>({
    queryKey: ["interviews"],
    queryFn: () => api.get<Interview[]>("/interviews"),
  });

  const resumes = useMemo(() => resumesQuery.data ?? [], [resumesQuery.data]);

  useEffect(() => {
    if (!resumeId && resumes.length) setResumeId(resumes[0].id);
  }, [resumeId, resumes]);

  const startMutation = useMutation({
    mutationFn: () =>
      api.post<Interview>("/interviews", {
        resume_id: resumeId,
        role,
        target_role: user?.target_role ?? null,
      }),
    onSuccess: (interview) => {
      queryClient.invalidateQueries({ queryKey: ["interviews"] });
      router.push(`/interview/${interview.id}`);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : "Could not start the interview."),
  });

  const rubric = rubricQuery.data;
  const interviews = interviewsQuery.data ?? [];

  return (
    <>
      <PageHeading
        eyebrow="Practice room"
        title={t("title")}
        subtitle={t("subtitle")}
        actions={
          resumes.length ? (
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus /> {t("newInterview")}
                </Button>
              </DialogTrigger>
              <DialogContent title={t("newInterview")} description={t("hint")}>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="resume">{t("resume")}</Label>
                    <Select
                      id="resume"
                      value={resumeId}
                      onChange={(event) => setResumeId(event.target.value)}
                    >
                      {resumes.map((resume) => (
                        <option key={resume.id} value={resume.id}>
                          {resume.filename}
                        </option>
                      ))}
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="role">{t("role")}</Label>
                    <Select
                      id="role"
                      value={role}
                      onChange={(event) => setRole(event.target.value)}
                    >
                      {ROLE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </div>
                  {error ? (
                    <p className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">
                      {error}
                    </p>
                  ) : null}
                  <div className="flex items-start gap-2 rounded-xl border border-primary/20 bg-primary/5 p-3 text-[11px] text-muted">
                    <LockKeyhole className="mt-0.5 size-3.5 shrink-0 text-primary" />
                    The rubric is fixed before you start. The model cannot change weights, and your
                    score is stored with its rubric and prompt versions.
                  </div>
                  <Button
                    className="w-full"
                    loading={startMutation.isPending}
                    disabled={!resumeId}
                    onClick={() => startMutation.mutate()}
                  >
                    {startMutation.isPending ? t("starting") : t("start")}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          ) : (
            <Button asChild>
              <Link href="/dashboard/resume">
                <FileText /> {t("uploadFirst")}
              </Link>
            </Button>
          )
        }
      />

      <div className="grid gap-4 xl:grid-cols-12">
        <div className="space-y-4 xl:col-span-8">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>{t("history")}</CardTitle>
                <CardDescription>{t("roundTags")}</CardDescription>
              </div>
              <Badge variant="muted">{interviews.length}</Badge>
            </CardHeader>
            <CardContent>
              {interviewsQuery.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-20 w-full" />
                </div>
              ) : interviewsQuery.isError ? (
                <ErrorState
                  message="Could not load interviews."
                  onRetry={() => interviewsQuery.refetch()}
                />
              ) : interviews.length === 0 ? (
                <EmptyState
                  icon={MessagesSquare}
                  title={t("empty")}
                  body={t("emptyBody")}
                  action={
                    resumes.length ? (
                      <Button onClick={() => setOpen(true)}>{t("newInterview")}</Button>
                    ) : (
                      <Button asChild>
                        <Link href="/dashboard/resume">{t("uploadFirst")}</Link>
                      </Button>
                    )
                  }
                />
              ) : (
                <div className="space-y-2.5">
                  {interviews.map((interview) => (
                    <div
                      key={interview.id}
                      className="flex flex-col gap-3 rounded-xl border border-border bg-surface/40 p-3.5 transition-colors hover:border-primary/30 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="flex items-start gap-3">
                        <span
                          className={cn(
                            "flex size-10 shrink-0 items-center justify-center rounded-xl",
                            interview.status === "completed"
                              ? "bg-primary/10 text-primary"
                              : "bg-accent/10 text-accent",
                          )}
                        >
                          <MessagesSquare className="size-4" />
                        </span>
                        <div>
                          <p className="text-xs font-semibold">
                            {roleLabel(interview.role)} · {roundLabel(interview.current_round)}
                          </p>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] text-muted">
                            <span>
                              {formatRelative(interview.completed_at ?? interview.started_at)}
                            </span>
                            <span>·</span>
                            <span className="flex items-center gap-1">
                              <Clock className="size-3" />{" "}
                              {formatDuration(interview.duration_seconds)}
                            </span>
                            <Badge
                              variant={interview.status === "completed" ? "success" : "accent"}
                              className="px-1.5 py-0 text-[9px]"
                            >
                              {interview.status === "completed" ? t("completed") : t("inProgress")}
                            </Badge>
                            {interview.variance_flag ? (
                              <Badge variant="warning" className="px-1.5 py-0 text-[9px]">
                                {t("variance")}
                              </Badge>
                            ) : null}
                          </div>
                        </div>
                      </div>
                      <div className="pl-13 flex items-center gap-3 sm:pl-0">
                        {interview.overall_score !== null ? (
                          <span
                            className={cn(
                              "font-display text-xl font-semibold",
                              scoreTone(interview.overall_score),
                            )}
                          >
                            {Math.round(interview.overall_score)}
                          </span>
                        ) : null}
                        {interview.status === "completed" ? (
                          <Button asChild size="sm" variant="secondary">
                            <Link href={`/interview/${interview.id}/feedback`}>{t("review")}</Link>
                          </Button>
                        ) : (
                          <Button asChild size="sm">
                            <Link href={`/interview/${interview.id}`}>
                              <Play /> {t("continue")}
                            </Link>
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4 xl:col-span-4">
          <Card className="relative overflow-hidden border-primary/20">
            <div className="pointer-events-none absolute -right-12 -top-12 size-40 rounded-full bg-primary/20 blur-3xl" />
            <CardHeader>
              <div>
                <CardTitle>{t("rubricTitle")}</CardTitle>
                <CardDescription>{t("rubricHint")}</CardDescription>
              </div>
              <ShieldCheck className="size-4 text-primary" />
            </CardHeader>
            <CardContent>
              {rubricQuery.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-14 w-full" />
                  <Skeleton className="h-14 w-full" />
                </div>
              ) : rubric ? (
                <div className="space-y-2">
                  {rubric.criteria.map((criterion) => (
                    <div
                      key={criterion.key}
                      className="rounded-xl border border-border/70 bg-surface/40 p-3"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs font-semibold">{criterion.label}</p>
                        <span className="font-display text-xs text-primary">
                          {Math.round(criterion.weight * 100)}%
                        </span>
                      </div>
                      <p className="mt-1 text-[10px] leading-relaxed text-muted">
                        {criterion.description}
                      </p>
                    </div>
                  ))}
                  <p className="pt-1 text-[10px] text-muted">
                    {t("rubricVersion", { version: rubric.version })} · 0–10 per criterion
                  </p>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>How scoring works</CardTitle>
                <CardDescription>No mystery maths</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-2.5 text-[11px] text-muted">
              {[
                "Three low-temperature samples are generated per interview.",
                "Each criterion uses the median of the three samples.",
                "Overall = weighted rubric score, recomputed on the server.",
                "High variance is flagged for human review, never hidden.",
              ].map((item, index) => (
                <div key={item} className="flex gap-2.5">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[9px] font-bold text-primary">
                    {index + 1}
                  </span>
                  <p>{item}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <div className="rounded-2xl border border-dashed border-border p-4 text-[11px] text-muted">
            <p className="flex items-center gap-1.5 font-semibold text-fg">
              <LockKeyhole className="size-3.5 text-accent" /> Voice interviews in Phase 2
            </p>
            <p className="mt-1">
              Phase 1 is text-only by design: no raw audio is collected, so there is no audio
              retention risk while the platform is being validated.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
