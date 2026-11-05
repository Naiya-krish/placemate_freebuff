"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  ArrowLeft,
  ArrowRight,
  BriefcaseBusiness,
  CheckCircle2,
  FileText,
  GraduationCap,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { Brand } from "@/components/brand";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { ThemeToggle } from "@/components/theme-provider";
import { ReadinessRing } from "@/components/charts/readiness-ring";
import { Confetti } from "@/components/confetti";
import { Button } from "@/components/ui/button";

import { ApiError, api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useRequireAuth } from "@/hooks/use-session";
import type { Analysis, AuthResponse, Resume } from "@/lib/types";
import { cn } from "@/lib/utils";

const BRANCHES = ["CSE", "IT", "ECE", "EEE", "MECH", "CIVIL", "AI & DS"];
const ROLES = [
  { label: "Software Engineer", icon: GraduationCap },
  { label: "Data Analyst", icon: BriefcaseBusiness },
  { label: "Product Manager", icon: Sparkles },
  { label: "Core Electronics", icon: GraduationCap },
];

const DEFAULT_JD =
  "We hire final-year students with strong fundamentals, practical project experience, testing discipline and clear communication. Cloud deployment experience is a plus.";

export default function OnboardingPage() {
  const t = useTranslations("onboarding");
  const router = useRouter();
  const { user, ready } = useRequireAuth(["student"]);
  const { setUser } = useAuthStore();
  const [step, setStep] = useState(0);
  const [branch, setBranch] = useState("CSE");
  const [role, setRole] = useState("Software Engineer");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [celebrate, setCelebrate] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (user?.branch) setBranch(user.branch);
    if (user?.target_role) setRole(user.target_role);
  }, [user?.branch, user?.target_role]);

  useEffect(() => {
    if (!analysis) return;
    setCelebrate(true);
    const timer = setTimeout(() => setCelebrate(false), 3000);
    return () => clearTimeout(timer);
  }, [analysis]);

  const progress = useMemo(() => ((step + 1) / 3) * 100, [step]);

  async function saveProfile() {
    const updated = await api.patch<AuthResponse["user"]>("/auth/onboarding", {
      branch,
      target_role: role,
      complete: true,
    });
    setUser(updated);
  }

  async function finish() {
    if (uploading) return;
    try {
      await saveProfile();
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save your profile.");
    }
  }

  async function uploadAndScore() {
    if (!file) return;
    setError(null);
    if (file.size > 5 * 1024 * 1024) {
      setError("That file is larger than 5 MB.");
      return;
    }
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const resume = await api.upload<Resume>("/resumes", form);
      const result = await api.post<Analysis>(`/resumes/${resume.id}/analyze`, {
        job_description: DEFAULT_JD,
        target_role: role,
      });
      setAnalysis(result);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Upload failed. Try a PDF or DOCX under 5 MB.",
      );
    } finally {
      setUploading(false);
    }
  }

  if (!ready || !user) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg text-sm text-muted">
        Loading…
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-bg">
      <Confetti fire={celebrate} />
      <header className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4 md:px-6">
        <Brand />
        <div className="flex items-center gap-2">
          <LocaleSwitcher />
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-16 pt-4 md:px-6">
        <div className="mb-8 text-center">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-primary">
            {t("step", { current: step + 1 })}
          </p>
          <h1 className="mt-2 font-display text-2xl font-semibold sm:text-3xl">
            {analysis ? t("firstWin") : t("welcome")}
          </h1>
          {!analysis ? <p className="mt-2 text-sm text-muted">{t("welcomeSub")}</p> : null}
          <div className="mx-auto mt-5 h-1.5 max-w-xs overflow-hidden rounded-full bg-border/60">
            <div
              className="h-full rounded-full bg-brand-gradient transition-all duration-500"
              style={{ width: `${analysis ? 100 : progress}%` }}
            />
          </div>
        </div>

        <div className="surface-card p-5 md:p-7">
          {analysis ? (
            <div className="flex flex-col items-center gap-6 py-4 text-center sm:flex-row sm:text-left">
              <ReadinessRing
                score={analysis.score}
                label={t("scoreReady", { score: analysis.score })}
                size={160}
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 text-sm font-semibold text-success">
                  <CheckCircle2 className="size-4" /> {t("firstWin")}
                </div>
                <p className="mt-2 text-sm text-muted">
                  {analysis.suggestions.length} safe edits found ·{" "}
                  {analysis.missing_evidence.length} pieces of evidence to add.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button onClick={finish}>
                    {t("finish")} <ArrowRight />
                  </Button>
                  <Button variant="ghost" onClick={() => router.push("/dashboard/resume")}>
                    Review suggestions
                  </Button>
                </div>
                <p className="mt-3 text-[10px] text-muted">{t("resumeOptional")}</p>
              </div>
            </div>
          ) : step === 0 ? (
            <div>
              <h2 className="text-lg font-semibold">{t("branchTitle")}</h2>
              <p className="mt-1 text-sm text-muted">{t("branchSub")}</p>
              <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3">
                {BRANCHES.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setBranch(item)}
                    aria-pressed={branch === item}
                    className={cn(
                      "rounded-xl border px-4 py-3 text-sm font-semibold transition-all",
                      branch === item
                        ? "border-primary/60 bg-primary/10 text-fg shadow-glow"
                        : "border-border bg-surface text-muted hover:border-primary/30 hover:text-fg",
                    )}
                  >
                    {item}
                  </button>
                ))}
              </div>
              <div className="mt-6 flex justify-end">
                <Button onClick={() => setStep(1)}>
                  {t("welcome") === "Welcome" ? "Continue" : "आगे"} <ArrowRight />
                </Button>
              </div>
            </div>
          ) : step === 1 ? (
            <div>
              <h2 className="text-lg font-semibold">{t("roleTitle")}</h2>
              <p className="mt-1 text-sm text-muted">{t("roleSub")}</p>
              <div className="mt-5 grid gap-2 sm:grid-cols-2">
                {ROLES.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.label}
                      type="button"
                      onClick={() => setRole(item.label)}
                      aria-pressed={role === item.label}
                      className={cn(
                        "flex items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm font-semibold transition-all",
                        role === item.label
                          ? "border-primary/60 bg-primary/10 text-fg shadow-glow"
                          : "border-border bg-surface text-muted hover:border-primary/30 hover:text-fg",
                      )}
                    >
                      <Icon className="size-4" /> {item.label}
                    </button>
                  );
                })}
              </div>
              <div className="mt-6 flex justify-between">
                <Button variant="ghost" onClick={() => setStep(0)}>
                  <ArrowLeft /> Back
                </Button>
                <Button onClick={() => setStep(2)}>
                  Continue <ArrowRight />
                </Button>
              </div>
            </div>
          ) : (
            <div>
              <h2 className="text-lg font-semibold">{t("resumeTitle")}</h2>
              <p className="mt-1 text-sm text-muted">{t("resumeSub")}</p>
              <div
                className="mt-5 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-border bg-surface/40 px-6 py-10 text-center transition-colors hover:border-primary/50"
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => {
                  event.preventDefault();
                  const dropped = event.dataTransfer.files?.[0];
                  if (dropped) setFile(dropped);
                }}
                onClick={() => inputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
                }}
              >
                <span className="flex size-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary">
                  {file ? <FileText className="size-5" /> : <UploadCloud className="size-5" />}
                </span>
                <p className="text-sm font-semibold">{file ? file.name : t("drop")}</p>
                <p className="text-xs text-muted">
                  {file ? `${(file.size / 1024).toFixed(0)} KB` : t("browse")}
                </p>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  className="sr-only"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </div>

              {error ? (
                <p
                  role="alert"
                  className="mt-3 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger"
                >
                  {error}
                </p>
              ) : null}

              {uploading ? (
                <div className="mt-4 flex items-center gap-3 rounded-xl border border-accent/20 bg-accent/5 px-4 py-3 text-xs text-accent">
                  <span className="size-2 animate-pulse rounded-full bg-accent" />
                  {t("analyzing")}
                </div>
              ) : null}

              <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
                <Button variant="ghost" onClick={() => setStep(1)} disabled={uploading}>
                  <ArrowLeft /> Back
                </Button>
                <div className="flex gap-2">
                  <Button variant="ghost" onClick={finish} disabled={uploading}>
                    {t("skip")}
                  </Button>
                  <Button onClick={uploadAndScore} loading={uploading} disabled={!file}>
                    {t("upload")} <ArrowRight />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>

        <p className="mt-6 text-center text-[10px] text-muted">
          Your resume is untrusted input to the AI. Instructions inside it are ignored, and every
          generated edit is checked against your real experience.
        </p>
      </main>
    </div>
  );
}
