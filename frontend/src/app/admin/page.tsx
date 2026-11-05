"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  BookOpenCheck,
  Building2,
  CheckCircle2,
  Plus,
  Sparkles,
  Trash2,
  Users,
} from "lucide-react";
import { ErrorState, PageHeading } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SegmentedTabs } from "@/components/ui/tabs";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/stat-card";
import { api, ApiError } from "@/lib/api";
import type { AdminOverview, College, Question, RubricVersion } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";

const STANDARD_CRITERIA = [
  {
    key: "clarity",
    label: "Clarity",
    weight: 0.18,
    description: "Structured, concise and easy to follow.",
  },
  {
    key: "technical_depth",
    label: "Technical depth",
    weight: 0.24,
    description: "Mechanisms, constraints and trade-offs.",
  },
  {
    key: "problem_solving",
    label: "Problem solving",
    weight: 0.22,
    description: "Reasoned approach and validation.",
  },
  {
    key: "communication",
    label: "Communication",
    weight: 0.16,
    description: "Answers the question and adapts.",
  },
  { key: "role_fit", label: "Role fit", weight: 0.2, description: "Evidence for the target role." },
];

export default function AdminPage() {
  const t = useTranslations("admin");
  const tc = useTranslations("common");
  const queryClient = useQueryClient();
  const [tab, setTab] = useState("overview");
  const [error, setError] = useState<string | null>(null);

  const overviewQuery = useQuery<AdminOverview>({
    queryKey: ["admin-overview"],
    queryFn: () => api.get<AdminOverview>("/admin/overview"),
  });
  const collegesQuery = useQuery<College[]>({
    queryKey: ["admin-colleges"],
    queryFn: () => api.get<College[]>("/admin/colleges"),
  });
  const questionsQuery = useQuery<Question[]>({
    queryKey: ["admin-questions"],
    queryFn: () => api.get<Question[]>("/admin/questions"),
  });
  const rubricsQuery = useQuery<RubricVersion[]>({
    queryKey: ["admin-rubrics"],
    queryFn: () => api.get<RubricVersion[]>("/admin/rubrics"),
  });

  const [collegeForm, setCollegeForm] = useState({
    name: "",
    code: "",
    city: "",
    placement_date: "",
  });
  const [questionForm, setQuestionForm] = useState({
    prompt: "",
    ideal_answer: "",
    role: "swe",
    topic: "technical",
    difficulty: "medium",
    key_points: "",
    is_global: false,
  });
  const [rubricForm, setRubricForm] = useState({ version: "", label: "" });

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 6000);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [error]);

  const createCollege = useMutation({
    mutationFn: () =>
      api.post<College>("/admin/colleges", {
        name: collegeForm.name,
        code: collegeForm.code.toUpperCase(),
        city: collegeForm.city || null,
        placement_date: collegeForm.placement_date || null,
      }),
    onSuccess: () => {
      setCollegeForm({ name: "", code: "", city: "", placement_date: "" });
      queryClient.invalidateQueries({ queryKey: ["admin-colleges"] });
      queryClient.invalidateQueries({ queryKey: ["admin-overview"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t("error")),
  });

  const createQuestion = useMutation({
    mutationFn: () =>
      api.post<Question>("/admin/questions", {
        ...questionForm,
        key_points: questionForm.key_points
          .split(",")
          .map((point) => point.trim())
          .filter(Boolean),
      }),
    onSuccess: () => {
      setQuestionForm((current) => ({
        ...current,
        prompt: "",
        ideal_answer: "",
        key_points: "",
        is_global: false,
      }));
      queryClient.invalidateQueries({ queryKey: ["admin-questions"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t("error")),
  });

  const deleteQuestion = useMutation({
    mutationFn: (id: string) => api.delete<void>(`/admin/questions/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-questions"] }),
    onError: (err) => setError(err instanceof ApiError ? err.message : t("error")),
  });

  const createRubric = useMutation({
    mutationFn: () =>
      api.post<RubricVersion>("/admin/rubrics", {
        version: rubricForm.version,
        label: rubricForm.label || "Custom rubric",
        criteria: STANDARD_CRITERIA,
        activate: true,
      }),
    onSuccess: () => {
      setRubricForm({ version: "", label: "" });
      queryClient.invalidateQueries({ queryKey: ["admin-rubrics"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t("error")),
  });

  const activateRubric = useMutation({
    mutationFn: (id: string) => api.post<RubricVersion>(`/admin/rubrics/${id}/activate`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-rubrics"] }),
    onError: (err) => setError(err instanceof ApiError ? err.message : t("error")),
  });

  const overview = overviewQuery.data;

  return (
    <>
      <PageHeading
        eyebrow="Platform"
        title={t("title")}
        subtitle={t("subtitle")}
        actions={<Badge variant="accent">Admin only</Badge>}
      />

      {error ? (
        <p
          role="alert"
          className="mb-4 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger"
        >
          {error}
        </p>
      ) : null}

      <SegmentedTabs
        value={tab}
        onChange={setTab}
        className="mb-4 w-fit"
        items={[
          { value: "overview", label: t("overview") },
          { value: "colleges", label: t("colleges") },
          { value: "questions", label: t("questions") },
          { value: "rubrics", label: t("rubrics") },
        ]}
      />

      {tab === "overview" ? (
        overviewQuery.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-24 w-full" />
            ))}
          </div>
        ) : overview ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard label={t("totalColleges")} value={overview.colleges} icon={Building2} />
              <StatCard
                label={t("totalStudents")}
                value={overview.students}
                icon={Users}
                tone="accent"
              />
              <StatCard
                label={t("totalInterviews")}
                value={overview.interviews}
                icon={BookOpenCheck}
                tone="primary"
              />
              <StatCard
                label={t("totalSpend")}
                value={formatCurrency(overview.usage.reduce((sum, row) => sum + row.cost_usd, 0))}
                icon={Sparkles}
                tone="success"
              />
            </div>
            <Card className="mt-4">
              <CardHeader>
                <div>
                  <CardTitle>{t("usage")}</CardTitle>
                  <CardDescription>{t("usageHint")}</CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                {overview.usage.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted">{t("empty")}</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[480px] text-left text-xs">
                      <thead>
                        <tr className="border-b border-border text-[10px] uppercase tracking-wide text-muted">
                          <th className="pb-2">{t("colleges")}</th>
                          <th className="pb-2">Month</th>
                          <th className="pb-2 text-right">{t("tokens")}</th>
                          <th className="pb-2 text-right">{t("billedUsers")}</th>
                          <th className="pb-2 text-right">{t("cost")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {overview.usage.map((row) => (
                          <tr
                            key={`${row.college_id}-${row.month}`}
                            className="border-b border-border/50"
                          >
                            <td className="py-2.5 font-semibold">{row.college_name}</td>
                            <td className="py-2.5 text-muted">{row.month}</td>
                            <td className="py-2.5 text-right tabular-nums">
                              {row.tokens.toLocaleString()}
                            </td>
                            <td className="py-2.5 text-right tabular-nums">{row.users_billable}</td>
                            <td className="py-2.5 text-right font-display tabular-nums">
                              {formatCurrency(row.cost_usd)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        ) : (
          <ErrorState message={t("empty")} onRetry={() => overviewQuery.refetch()} />
        )
      ) : null}

      {tab === "colleges" ? (
        <div className="grid gap-4 lg:grid-cols-12">
          <Card className="lg:col-span-5">
            <CardHeader>
              <div>
                <CardTitle>{t("addCollege")}</CardTitle>
                <CardDescription>
                  Each college gets its own tenant, rubric and analytics.
                </CardDescription>
              </div>
              <Building2 className="size-4 text-muted" />
            </CardHeader>
            <CardContent>
              <form
                className="space-y-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  createCollege.mutate();
                }}
              >
                <div>
                  <Label htmlFor="college-name">{t("collegeName")}</Label>
                  <Input
                    id="college-name"
                    required
                    value={collegeForm.name}
                    onChange={(event) =>
                      setCollegeForm({ ...collegeForm, name: event.target.value })
                    }
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="college-code">{t("collegeCode")}</Label>
                    <Input
                      id="college-code"
                      required
                      value={collegeForm.code}
                      onChange={(event) =>
                        setCollegeForm({ ...collegeForm, code: event.target.value.toUpperCase() })
                      }
                      placeholder="NOVA"
                    />
                  </div>
                  <div>
                    <Label htmlFor="college-city">{t("city")}</Label>
                    <Input
                      id="college-city"
                      value={collegeForm.city}
                      onChange={(event) =>
                        setCollegeForm({ ...collegeForm, city: event.target.value })
                      }
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="placement-date">{t("placementDate")}</Label>
                  <Input
                    id="placement-date"
                    type="date"
                    value={collegeForm.placement_date}
                    onChange={(event) =>
                      setCollegeForm({ ...collegeForm, placement_date: event.target.value })
                    }
                  />
                </div>
                <Button type="submit" className="w-full" loading={createCollege.isPending}>
                  <Plus /> {t("create")}
                </Button>
              </form>
            </CardContent>
          </Card>
          <Card className="lg:col-span-7">
            <CardHeader>
              <div>
                <CardTitle>{t("colleges")}</CardTitle>
                <CardDescription>{collegesQuery.data?.length ?? 0} tenants</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {(collegesQuery.data ?? []).map((college) => (
                <div
                  key={college.id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-surface/40 px-3 py-2.5"
                >
                  <div>
                    <p className="text-xs font-semibold">{college.name}</p>
                    <p className="text-[10px] text-muted">
                      {college.code} · {college.city ?? "—"} · drive{" "}
                      {formatDate(college.placement_date)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="muted">
                      {college.student_count} {t("students")}
                    </Badge>
                    <Badge variant={college.is_active ? "success" : "danger"}>
                      {college.is_active ? "Active" : "Off"}
                    </Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      ) : null}

      {tab === "questions" ? (
        <div className="grid gap-4 lg:grid-cols-12">
          <Card className="lg:col-span-5">
            <CardHeader>
              <div>
                <CardTitle>{t("addQuestion")}</CardTitle>
                <CardDescription>
                  Embeddings are generated automatically for retrieval.
                </CardDescription>
              </div>
              <Plus className="size-4 text-muted" />
            </CardHeader>
            <CardContent>
              <form
                className="space-y-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  createQuestion.mutate();
                }}
              >
                <div>
                  <Label htmlFor="question-prompt">{t("questionPrompt")}</Label>
                  <Textarea
                    id="question-prompt"
                    required
                    minLength={8}
                    value={questionForm.prompt}
                    onChange={(event) =>
                      setQuestionForm({ ...questionForm, prompt: event.target.value })
                    }
                    className="min-h-[90px]"
                  />
                </div>
                <div>
                  <Label htmlFor="ideal-answer">{t("idealAnswer")}</Label>
                  <Textarea
                    id="ideal-answer"
                    value={questionForm.ideal_answer}
                    onChange={(event) =>
                      setQuestionForm({ ...questionForm, ideal_answer: event.target.value })
                    }
                    className="min-h-[70px]"
                  />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <Label htmlFor="q-role">{t("role")}</Label>
                    <Select
                      id="q-role"
                      value={questionForm.role}
                      onChange={(event) =>
                        setQuestionForm({ ...questionForm, role: event.target.value })
                      }
                    >
                      {["swe", "data", "product", "core", "general"].map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="q-topic">{t("topic")}</Label>
                    <Select
                      id="q-topic"
                      value={questionForm.topic}
                      onChange={(event) =>
                        setQuestionForm({ ...questionForm, topic: event.target.value })
                      }
                    >
                      {["project", "technical", "hr"].map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="q-difficulty">{t("difficulty")}</Label>
                    <Select
                      id="q-difficulty"
                      value={questionForm.difficulty}
                      onChange={(event) =>
                        setQuestionForm({ ...questionForm, difficulty: event.target.value })
                      }
                    >
                      {["easy", "medium", "hard"].map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </Select>
                  </div>
                </div>
                <div>
                  <Label htmlFor="key-points">{t("keyPoints")}</Label>
                  <Input
                    id="key-points"
                    value={questionForm.key_points}
                    onChange={(event) =>
                      setQuestionForm({ ...questionForm, key_points: event.target.value })
                    }
                  />
                </div>
                <label className="flex items-start gap-2 text-xs text-muted">
                  <input
                    type="checkbox"
                    checked={questionForm.is_global}
                    onChange={(event) =>
                      setQuestionForm({ ...questionForm, is_global: event.target.checked })
                    }
                    className="mt-0.5 size-4 accent-[hsl(var(--primary))]"
                  />
                  <span>
                    {t("globalQuestion")}
                    <span className="block text-[10px]">{t("globalNote")}</span>
                  </span>
                </label>
                <Button type="submit" className="w-full" loading={createQuestion.isPending}>
                  <Plus /> {t("addQuestion")}
                </Button>
              </form>
            </CardContent>
          </Card>
          <Card className="lg:col-span-7">
            <CardHeader>
              <div>
                <CardTitle>{t("questions")}</CardTitle>
                <CardDescription>{questionsQuery.data?.length ?? 0} questions</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="max-h-[560px] space-y-2 overflow-y-auto pr-1">
              {(questionsQuery.data ?? []).map((question) => (
                <div
                  key={question.id}
                  className="rounded-xl border border-border/70 bg-surface/40 p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs leading-relaxed">{question.prompt}</p>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        <Badge variant="muted" className="px-1.5 py-0 text-[9px]">
                          {question.role}
                        </Badge>
                        <Badge variant="default" className="px-1.5 py-0 text-[9px]">
                          {question.topic}
                        </Badge>
                        <Badge variant="outline" className="px-1.5 py-0 text-[9px]">
                          {question.difficulty}
                        </Badge>
                        {question.college_id === null ? (
                          <Badge variant="accent" className="px-1.5 py-0 text-[9px]">
                            global
                          </Badge>
                        ) : null}
                        {!question.is_active ? (
                          <Badge variant="danger" className="px-1.5 py-0 text-[9px]">
                            inactive
                          </Badge>
                        ) : null}
                      </div>
                    </div>
                    {question.college_id ? (
                      <button
                        type="button"
                        aria-label="Deactivate question"
                        onClick={() => deleteQuestion.mutate(question.id)}
                        className="rounded-lg border border-border p-1.5 text-muted transition-colors hover:border-danger/40 hover:text-danger"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      ) : null}

      {tab === "rubrics" ? (
        <div className="grid gap-4 lg:grid-cols-12">
          <Card className="lg:col-span-5">
            <CardHeader>
              <div>
                <CardTitle>{t("newRubric")}</CardTitle>
                <CardDescription>{t("newRubricHint")}</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <form
                className="space-y-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  createRubric.mutate();
                }}
              >
                <div>
                  <Label htmlFor="rubric-version">{t("rubricVersion")}</Label>
                  <Input
                    id="rubric-version"
                    required
                    value={rubricForm.version}
                    onChange={(event) =>
                      setRubricForm({ ...rubricForm, version: event.target.value })
                    }
                    placeholder="v2"
                  />
                </div>
                <div>
                  <Label htmlFor="rubric-label">{t("rubricLabel")}</Label>
                  <Input
                    id="rubric-label"
                    value={rubricForm.label}
                    onChange={(event) =>
                      setRubricForm({ ...rubricForm, label: event.target.value })
                    }
                    placeholder="Spring 2026 rubric"
                  />
                </div>
                <div className="rounded-xl border border-border/70 bg-surface/40 p-3">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted">
                    {t("criteria")}
                  </p>
                  {STANDARD_CRITERIA.map((criterion) => (
                    <div key={criterion.key} className="flex justify-between py-0.5 text-[11px]">
                      <span>{criterion.label}</span>
                      <span className="text-primary">{Math.round(criterion.weight * 100)}%</span>
                    </div>
                  ))}
                </div>
                <Button type="submit" className="w-full" loading={createRubric.isPending}>
                  <Plus /> {t("newRubric")}
                </Button>
              </form>
            </CardContent>
          </Card>
          <Card className="lg:col-span-7">
            <CardHeader>
              <div>
                <CardTitle>{t("rubrics")}</CardTitle>
                <CardDescription>Versioned and immutable once used for scoring</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {(rubricsQuery.data ?? []).map((rubric) => (
                <div
                  key={rubric.id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-surface/40 p-3"
                >
                  <div>
                    <p className="text-xs font-semibold">
                      {rubric.version} · {rubric.label}
                    </p>
                    <p className="text-[10px] text-muted">
                      {rubric.criteria.length} criteria · {formatDate(rubric.created_at)}
                    </p>
                  </div>
                  {rubric.is_active ? (
                    <Badge variant="success">
                      <CheckCircle2 className="size-3" /> {t("active")}
                    </Badge>
                  ) : (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => activateRubric.mutate(rubric.id)}
                      loading={activateRubric.isPending && activateRubric.variables === rubric.id}
                    >
                      {t("activate")}
                    </Button>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      ) : null}

      <p className="mt-5 text-center text-[10px] text-muted">
        {tc("optional")} · Global questions are platform seeds. College questions are isolated by
        tenant.
      </p>
    </>
  );
}
