"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  BarChart3,
  CalendarDays,
  Download,
  EyeOff,
  FileText,
  GraduationCap,
  LockKeyhole,
  MailCheck,
  TrendingUp,
  Users,
} from "lucide-react";
import { ErrorState, PageHeading } from "@/components/app-shell";
import { CohortChart } from "@/components/charts/cohort-chart";
import { DepartmentHeatmap } from "@/components/charts/heatmap";
import { ReadinessFunnel } from "@/components/charts/funnel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/stat-card";
import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { OfficerOverview } from "@/lib/types";
import { formatDate, readinessBand, scoreTone } from "@/lib/utils";

export default function OfficerPage() {
  const t = useTranslations("officer");
  const user = useAuthStore((state) => state.user);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const overviewQuery = useQuery<OfficerOverview>({
    queryKey: ["officer-overview"],
    queryFn: () => api.get<OfficerOverview>("/officer/overview"),
  });
  const data = overviewQuery.data;

  async function exportPdf() {
    setExporting(true);
    setError(null);
    try {
      const blob = await api.blob("/officer/report.pdf");
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "placemate-cohort-readiness.pdf";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "PDF export failed.");
    } finally {
      setExporting(false);
    }
  }

  if (overviewQuery.isLoading) {
    return (
      <>
        <PageHeading title={t("title")} subtitle={t("subtitle")} />
        <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full" />
          ))}
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-80 w-full" />
          <Skeleton className="h-80 w-full" />
        </div>
      </>
    );
  }

  if (overviewQuery.isError || !data) {
    return (
      <>
        <PageHeading title={t("title")} subtitle={t("subtitle")} />
        <ErrorState
          message="Cohort analytics could not be loaded."
          onRetry={() => overviewQuery.refetch()}
        />
      </>
    );
  }

  const k = data.kpis;

  return (
    <>
      <PageHeading
        eyebrow="Placement cell"
        title={t("title")}
        subtitle={t("subtitle")}
        actions={
          <>
            <Badge variant="success" className="h-8 gap-1.5">
              <LockKeyhole className="size-3" /> {t("aggregate")}
            </Badge>
            <Button onClick={exportPdf} loading={exporting} variant="secondary">
              <Download /> {exporting ? t("exporting") : t("export")}
            </Button>
          </>
        }
      />

      {error ? (
        <p
          role="alert"
          className="mb-4 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger"
        >
          {error}
        </p>
      ) : null}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <StatCard label={t("students")} value={k.total_students} icon={Users} />
        <StatCard label={t("active")} value={k.active_30d} icon={TrendingUp} tone="success" />
        <StatCard label={t("resumes")} value={k.resume_uploads} icon={FileText} tone="accent" />
        <StatCard
          label={t("interviews")}
          value={k.interviews_completed}
          icon={BarChart3}
          tone="primary"
        />
        <StatCard
          label={t("readiness")}
          value={k.avg_readiness}
          hint={readinessBand(k.avg_readiness).label}
          icon={GraduationCap}
          tone={k.avg_readiness >= 70 ? "success" : "warning"}
        />
        <StatCard
          label={t("drive")}
          value={k.days_to_placement ?? "—"}
          hint={formatDate(k.placement_date)}
          icon={CalendarDays}
        />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-12">
        <Card className="xl:col-span-8">
          <CardHeader>
            <div>
              <CardTitle>{t("heatmap")}</CardTitle>
              <CardDescription>{t("heatmapHint")}</CardDescription>
            </div>
            <Badge variant="muted">{data.branches.length} branches</Badge>
          </CardHeader>
          <CardContent>
            <DepartmentHeatmap
              branches={data.branches}
              criteria={data.criteria}
              cells={data.heatmap}
            />
          </CardContent>
        </Card>

        <Card className="xl:col-span-4">
          <CardHeader>
            <div>
              <CardTitle>{t("weakest")}</CardTitle>
              <CardDescription>{t("weakestHint")}</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {data.weakest_skills.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted">{t("noData")}</p>
            ) : (
              data.weakest_skills.map((skill) => (
                <div key={skill.skill}>
                  <div className="mb-1.5 flex items-baseline justify-between">
                    <p className="text-xs font-semibold">{skill.skill}</p>
                    <p className="text-[10px] text-muted">
                      {t("gap")} {skill.gap} · {t("affected", { count: skill.students_affected })}
                    </p>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-surface">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-warning to-danger"
                      style={{ width: `${Math.min(100, skill.gap)}%` }}
                    />
                  </div>
                </div>
              ))
            )}
            <p className="border-t border-border/60 pt-3 text-[10px] leading-relaxed text-muted">
              {t("privacyNote")}
            </p>
          </CardContent>
        </Card>

        <Card className="xl:col-span-4">
          <CardHeader>
            <div>
              <CardTitle>{t("funnel")}</CardTitle>
              <CardDescription>{t("funnelHint")}</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <ReadinessFunnel stages={data.funnel} />
          </CardContent>
        </Card>

        <Card className="xl:col-span-8">
          <CardHeader>
            <div>
              <CardTitle>{t("cohort")}</CardTitle>
              <CardDescription>{t("cohortHint")}</CardDescription>
            </div>
            <MailCheck className="size-4 text-muted" />
          </CardHeader>
          <CardContent>
            <CohortChart data={data.cohort_progress} />
          </CardContent>
        </Card>

        <Card className="xl:col-span-7">
          <CardHeader>
            <div>
              <CardTitle>{t("batches")}</CardTitle>
              <CardDescription>Readiness, volume and resume coverage by branch</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[440px] text-left text-xs">
                <thead>
                  <tr className="border-b border-border text-[10px] uppercase tracking-wide text-muted">
                    <th className="pb-2 font-semibold">{t("batch")}</th>
                    <th className="pb-2 text-right font-semibold">{t("students")}</th>
                    <th className="pb-2 text-right font-semibold">{t("readiness")}</th>
                    <th className="pb-2 text-right font-semibold">{t("resumes")}</th>
                    <th className="pb-2 text-right font-semibold">{t("interviewsShort")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.batch_comparison.map((row) => (
                    <tr key={row.branch} className="border-b border-border/50">
                      <td className="py-2.5 font-semibold">{row.branch}</td>
                      <td className="py-2.5 text-right tabular-nums">{row.students}</td>
                      <td
                        className={`py-2.5 text-right font-display font-semibold tabular-nums ${scoreTone(row.readiness)}`}
                      >
                        {row.readiness || "—"}
                      </td>
                      <td className="py-2.5 text-right tabular-nums text-muted">{row.resumes}</td>
                      <td className="py-2.5 text-right tabular-nums text-muted">
                        {row.interviews}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card className="xl:col-span-5">
          <CardHeader>
            <div>
              <CardTitle>{t("studentsList")}</CardTitle>
              <CardDescription>{t("studentsHint")}</CardDescription>
            </div>
            <EyeOff className="size-4 text-muted" />
          </CardHeader>
          <CardContent>
            <div className="max-h-[330px] space-y-2 overflow-y-auto pr-1">
              {data.students.map((student) => (
                <div
                  key={student.id}
                  className="flex items-center justify-between gap-2 rounded-xl border border-border/70 bg-surface/35 px-3 py-2.5"
                >
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold">
                      {student.display_name}
                      {!student.consent ? (
                        <span className="ml-1.5 text-[9px] text-muted">({t("hidden")})</span>
                      ) : null}
                    </p>
                    <p className="text-[10px] text-muted">
                      {student.branch ?? "—"} ·{" "}
                      {student.consent ? `${student.interviews} interviews` : t("hiddenNote")}
                    </p>
                  </div>
                  {student.consent ? (
                    <div className="text-right">
                      <p
                        className={`font-display text-sm font-semibold ${scoreTone(student.readiness ?? 0)}`}
                      >
                        {student.readiness ?? "—"}
                      </p>
                      <Badge variant="success" className="px-1.5 py-0 text-[8px]">
                        {t("consented")}
                      </Badge>
                    </div>
                  ) : (
                    <LockKeyhole className="size-3.5 shrink-0 text-muted/60" />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <p className="mt-5 text-center text-[10px] text-muted">
        Generated {new Date(data.generated_at).toLocaleString()} · Signed in as {user?.name} ·{" "}
        {data.aggregate_only ? "aggregate-only mode" : "mixed mode"}
      </p>
    </>
  );
}
