"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  FileText,
  Info,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import { PageHeading } from "@/components/app-shell";
import { ReadinessRing } from "@/components/charts/readiness-ring";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { Analysis, Resume } from "@/lib/types";
import { cn, formatBytes, formatDate, scoreTone } from "@/lib/utils";

const MAX_BYTES = 5 * 1024 * 1024;

export default function ResumePage() {
  const t = useTranslations("resume");
  const user = useAuthStore((state) => state.user);
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [targetRole, setTargetRole] = useState(user?.target_role ?? "Software Engineer");
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const resumesQuery = useQuery<Resume[]>({
    queryKey: ["resumes"],
    queryFn: () => api.get<Resume[]>("/resumes"),
  });
  const resumes = useMemo(() => resumesQuery.data ?? [], [resumesQuery.data]);

  useEffect(() => {
    if (!selectedId && resumes.length > 0) setSelectedId(resumes[0].id);
  }, [resumes, selectedId]);

  const analysesQuery = useQuery<Analysis[]>({
    queryKey: ["analyses", selectedId],
    queryFn: () => api.get<Analysis[]>(`/resumes/${selectedId}/analyses`),
    enabled: Boolean(selectedId),
  });
  const analysis = analysesQuery.data?.[0] ?? null;

  const uploadMutation = useMutation({
    mutationFn: async (picked: File) => {
      const form = new FormData();
      form.append("file", picked);
      return api.upload<Resume>("/resumes", form);
    },
    onSuccess: (resume) => {
      setFile(null);
      setSelectedId(resume.id);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : t("errorUpload"));
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: () =>
      api.post<Analysis>(`/resumes/${selectedId}/analyze`, {
        job_description: jobDescription,
        target_role: targetRole,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["analyses", selectedId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setError(null);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Analysis failed."),
  });

  const decisionMutation = useMutation({
    mutationFn: ({ suggestionId, accept }: { suggestionId: string; accept: boolean }) =>
      api.patch<Analysis>(`/analyses/${analysis?.id}/suggestions/${suggestionId}`, { accept }),
    onSuccess: (updated) => {
      queryClient.setQueryData<Analysis[]>(["analyses", selectedId], (current) =>
        current ? [updated, ...current.slice(1)] : [updated],
      );
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : "Could not save that choice."),
  });

  const selectedResume = useMemo(
    () => resumes.find((resume) => resume.id === selectedId) ?? null,
    [resumes, selectedId],
  );

  function pickFile(picked: File | null) {
    setError(null);
    if (!picked) return;
    if (picked.size > MAX_BYTES) {
      setError("That file is larger than 5 MB.");
      return;
    }
    if (!/\.(pdf|docx)$/i.test(picked.name)) {
      setError("Only PDF and DOCX files are accepted.");
      return;
    }
    setFile(picked);
    uploadMutation.mutate(picked);
  }

  return (
    <>
      <PageHeading
        eyebrow="Resume intelligence"
        title={t("title")}
        subtitle={t("subtitle")}
        actions={
          <Button
            variant="secondary"
            onClick={() => fileInput.current?.click()}
            loading={uploadMutation.isPending}
          >
            <UploadCloud /> {t("uploadTitle")}
          </Button>
        }
      />

      <input
        ref={fileInput}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        className="sr-only"
        onChange={(event) => pickFile(event.target.files?.[0] ?? null)}
        aria-label="Upload resume"
      />

      {error ? (
        <p
          role="alert"
          className="mb-4 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger"
        >
          {error}
        </p>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-12">
        <div className="space-y-4 xl:col-span-4">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>{t("uploadTitle")}</CardTitle>
                <CardDescription>{t("uploadHint")}</CardDescription>
              </div>
              <FileText className="size-4 text-muted" />
            </CardHeader>
            <CardContent>
              <div
                role="button"
                tabIndex={0}
                onClick={() => fileInput.current?.click()}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") fileInput.current?.click();
                }}
                onDragOver={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(event) => {
                  event.preventDefault();
                  setDragging(false);
                  pickFile(event.dataTransfer.files?.[0] ?? null);
                }}
                className={cn(
                  "flex cursor-pointer flex-col items-center gap-2 rounded-2xl border border-dashed px-4 py-8 text-center transition-colors",
                  dragging
                    ? "border-accent bg-accent/5"
                    : "border-border bg-surface/30 hover:border-primary/50",
                )}
              >
                <span className="flex size-11 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
                  <UploadCloud className="size-5" />
                </span>
                <p className="text-sm font-semibold">
                  {uploadMutation.isPending ? t("uploading") : (file?.name ?? t("uploadTitle"))}
                </p>
                <p className="text-[11px] text-muted">PDF / DOCX · ≤ 5 MB</p>
              </div>
              {uploadMutation.isError ? (
                <p className="mt-2 text-[11px] text-danger">{t("errorUpload")}</p>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>{t("yourResumes")}</CardTitle>
                <CardDescription>{resumes.length} uploaded</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              {resumesQuery.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-14 w-full" />
                  <Skeleton className="h-14 w-full" />
                </div>
              ) : resumes.length === 0 ? (
                <p className="py-4 text-center text-xs text-muted">{t("noResumesBody")}</p>
              ) : (
                <div className="space-y-2">
                  {resumes.map((resume) => (
                    <button
                      key={resume.id}
                      type="button"
                      onClick={() => setSelectedId(resume.id)}
                      aria-pressed={selectedId === resume.id}
                      className={cn(
                        "w-full rounded-xl border px-3 py-2.5 text-left transition-colors",
                        selectedId === resume.id
                          ? "border-primary/50 bg-primary/5"
                          : "border-border bg-surface/40 hover:border-primary/30",
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-xs font-semibold">{resume.filename}</p>
                        {selectedId === resume.id ? (
                          <CheckCircle2 className="size-4 shrink-0 text-primary" />
                        ) : null}
                      </div>
                      <div className="mt-1 flex items-center gap-2 text-[10px] text-muted">
                        <span>{formatBytes(resume.size_bytes)}</span>
                        <span>·</span>
                        <span>{formatDate(resume.created_at)}</span>
                        {resume.status === "needs_review" ? (
                          <Badge variant="warning" className="ml-auto px-1.5 py-0 text-[9px]">
                            Review
                          </Badge>
                        ) : null}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>{t("targetRole")}</CardTitle>
                <CardDescription>{t("jdHint")}</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label htmlFor="target-role">{t("targetRole")}</Label>
                <Input
                  id="target-role"
                  value={targetRole}
                  onChange={(event) => setTargetRole(event.target.value)}
                  placeholder="Software Engineer"
                />
              </div>
              <div>
                <Label htmlFor="jd">{t("jobDescription")}</Label>
                <Textarea
                  id="jd"
                  value={jobDescription}
                  onChange={(event) => setJobDescription(event.target.value)}
                  placeholder={t("jdPlaceholder")}
                  className="min-h-[130px]"
                />
              </div>
              <Button
                className="w-full"
                disabled={!selectedId || analyzeMutation.isPending}
                loading={analyzeMutation.isPending}
                onClick={() => analyzeMutation.mutate()}
              >
                {analyzeMutation.isPending ? t("analyzing") : t("analyze")} <ArrowRight />
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4 xl:col-span-8">
          {!selectedId ? (
            <EmptyState
              icon={FileText}
              title={t("emptyTitle")}
              body={t("emptyBody")}
              action={
                <Button variant="secondary" onClick={() => fileInput.current?.click()}>
                  <UploadCloud /> {t("uploadTitle")}
                </Button>
              }
              className="surface-card py-20"
            />
          ) : analysesQuery.isLoading ? (
            <Card>
              <Skeleton className="mb-4 h-5 w-1/3" />
              <div className="grid gap-4 sm:grid-cols-[160px_1fr]">
                <Skeleton className="h-40 w-40 rounded-full" />
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-5/6" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              </div>
            </Card>
          ) : !analysis ? (
            <EmptyState
              icon={Sparkles}
              title={t("emptyTitle")}
              body={t("emptyBody")}
              action={
                <Button
                  onClick={() => analyzeMutation.mutate()}
                  loading={analyzeMutation.isPending}
                >
                  {t("analyze")}
                </Button>
              }
              className="surface-card py-20"
            />
          ) : (
            <>
              {selectedResume?.status === "needs_review" ? (
                <div className="flex items-start gap-3 rounded-2xl border border-warning/30 bg-warning/5 p-4 text-xs">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
                  <div>
                    <p className="font-semibold text-warning">{t("needsReview")}</p>
                    <p className="mt-0.5 text-muted">{t("needsReviewBody")}</p>
                  </div>
                </div>
              ) : null}

              {analysis.injection_flags.length > 0 ? (
                <div className="flex items-start gap-3 rounded-2xl border border-warning/30 bg-warning/5 p-4 text-xs">
                  <Info className="mt-0.5 size-4 shrink-0 text-warning" />
                  <div>
                    <p className="font-semibold text-warning">{t("injectionWarning")}</p>
                    <p className="mt-0.5 font-mono text-[10px] text-muted">
                      {analysis.injection_flags.join(", ")}
                    </p>
                  </div>
                </div>
              ) : null}

              <Card>
                <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
                  <ReadinessRing score={analysis.score} label={t("score")} size={150} stroke={11} />
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="accent">{analysis.target_role}</Badge>
                      <span className="text-[10px] text-muted">
                        {t("scoreModel", {
                          model: analysis.model,
                          prompt: analysis.prompt_version,
                        })}
                      </span>
                    </div>
                    <div className="mt-4 grid gap-2 sm:grid-cols-2">
                      {Object.entries(analysis.subscores).map(([key, value]) => (
                        <div key={key}>
                          <div className="mb-1 flex justify-between text-[10px] capitalize text-muted">
                            <span>{key}</span>
                            <span className={scoreTone(value)}>{value}</span>
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
                </div>
              </Card>

              <div className="grid gap-4 lg:grid-cols-12">
                <Card className="lg:col-span-8">
                  <CardHeader>
                    <div>
                      <CardTitle>{t("suggestions")}</CardTitle>
                      <CardDescription>{t("suggestionsHint")}</CardDescription>
                    </div>
                    <Badge variant="muted">{analysis.suggestions.length}</Badge>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {analysis.suggestions.length === 0 ? (
                      <p className="py-8 text-center text-sm text-muted">{t("noSuggestions")}</p>
                    ) : (
                      analysis.suggestions.map((suggestion) => {
                        const decided = suggestion.decision !== "pending";
                        return (
                          <article
                            key={suggestion.id}
                            className={cn(
                              "rounded-2xl border p-4 transition-colors",
                              suggestion.decision === "accepted"
                                ? "border-success/30 bg-success/5"
                                : suggestion.decision === "rejected"
                                  ? "border-border bg-surface/30 opacity-70"
                                  : "border-border bg-surface/40",
                            )}
                          >
                            <div className="mb-2 flex flex-wrap items-center gap-1.5">
                              <Badge variant="muted" className="capitalize">
                                {suggestion.target_section}
                              </Badge>
                              <Badge variant="default" className="capitalize">
                                {suggestion.category}
                              </Badge>
                              {suggestion.decision === "accepted" ? (
                                <Badge variant="success">
                                  <Check className="size-3" /> {t("accepted")}
                                </Badge>
                              ) : suggestion.decision === "rejected" ? (
                                <Badge variant="danger">
                                  <X className="size-3" /> {t("rejected")}
                                </Badge>
                              ) : null}
                            </div>
                            <div className="grid gap-2 sm:grid-cols-2">
                              <div className="rounded-xl border border-danger/15 bg-danger/5 p-3">
                                <p className="mb-1 text-[9px] font-semibold uppercase tracking-wider text-danger/80">
                                  Before
                                </p>
                                <p className="text-xs leading-relaxed text-muted line-through decoration-danger/30">
                                  {suggestion.original}
                                </p>
                              </div>
                              <div className="rounded-xl border border-success/20 bg-success/5 p-3">
                                <p className="mb-1 text-[9px] font-semibold uppercase tracking-wider text-success">
                                  After
                                </p>
                                <p className="text-xs leading-relaxed">{suggestion.improved}</p>
                              </div>
                            </div>
                            <p className="mt-2 text-[11px] text-muted">
                              <Sparkles className="mr-1 inline size-3 text-primary" />
                              {suggestion.rationale}
                            </p>
                            {!decided ? (
                              <div className="mt-3 flex gap-2">
                                <Button
                                  size="sm"
                                  variant="success"
                                  onClick={() =>
                                    decisionMutation.mutate({
                                      suggestionId: suggestion.id,
                                      accept: true,
                                    })
                                  }
                                  loading={
                                    decisionMutation.isPending &&
                                    decisionMutation.variables?.suggestionId === suggestion.id
                                  }
                                >
                                  <Check /> {t("accept")}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  onClick={() =>
                                    decisionMutation.mutate({
                                      suggestionId: suggestion.id,
                                      accept: false,
                                    })
                                  }
                                >
                                  <X /> {t("reject")}
                                </Button>
                              </div>
                            ) : null}
                          </article>
                        );
                      })
                    )}
                  </CardContent>
                </Card>

                <Card className="lg:col-span-4">
                  <CardHeader>
                    <div>
                      <CardTitle>{t("missingEvidence")}</CardTitle>
                      <CardDescription>{t("missingHint")}</CardDescription>
                    </div>
                    <AlertTriangle className="size-4 text-warning" />
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {analysis.missing_evidence.length === 0 ? (
                      <p className="py-6 text-center text-xs text-muted">No gaps detected.</p>
                    ) : (
                      analysis.missing_evidence.map((item, index) => (
                        <div
                          key={`${item.item}-${index}`}
                          className="rounded-xl border border-warning/20 bg-warning/5 p-3"
                        >
                          <p className="text-xs font-semibold text-warning">{item.item}</p>
                          <p className="mt-1 text-[11px] leading-relaxed text-muted">
                            {item.reason}
                          </p>
                        </div>
                      ))
                    )}
                    <p className="pt-2 text-[10px] leading-relaxed text-muted">
                      These are gaps, not suggestions. Add them only if they are true — the editor
                      will never fabricate them for you.
                    </p>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
