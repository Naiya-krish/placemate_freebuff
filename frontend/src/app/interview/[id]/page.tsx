"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  ArrowLeft,
  Clock,
  Lightbulb,
  Mic,
  Send,
  Sparkles,
  Square,
  Volume2,
  Zap,
} from "lucide-react";
import { BrandMark } from "@/components/brand";
import { ReadinessRing } from "@/components/charts/readiness-ring";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { ThemeToggle } from "@/components/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { WS_URL, api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useRequireAuth } from "@/hooks/use-session";
import type { InterviewDetail, Rubric } from "@/lib/types";
import { cn, formatDuration, roundLabel } from "@/lib/utils";

interface ChatTurn {
  speaker: "interviewer" | "candidate" | "system";
  content: string;
  round: string;
  followup?: boolean;
}

interface ScoreResult {
  overall: number;
  criteria: Array<{ key: string; label: string; score: number; weight: number }>;
}

const ROUNDS = ["project", "technical", "hr"] as const;

function socketUrl(id: string, token: string): string {
  const base = WS_URL.startsWith("/")
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}${WS_URL}`
    : WS_URL;
  return `${base}/interviews/${id}/ws?token=${encodeURIComponent(token)}`;
}

export default function InterviewRoomPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const t = useTranslations("interviews");
  const tc = useTranslations("common");
  const router = useRouter();
  const { ready } = useRequireAuth(["student"]);
  const token = useAuthStore((state) => state.accessToken);
  const [chat, setChat] = useState<ChatTurn[]>([]);
  const [answer, setAnswer] = useState("");
  const [status, setStatus] = useState<"connecting" | "live" | "closed">("connecting");
  const [typing, setTyping] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [rubric, setRubric] = useState<Rubric | null>(null);
  const [role, setRole] = useState("swe");
  const [currentRound, setCurrentRound] = useState<string>("project");
  const [finished, setFinished] = useState(false);
  const [score, setScore] = useState<ScoreResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [xp, setXp] = useState(0);
  const [seconds, setSeconds] = useState(0);
  const [hintsUsed, setHintsUsed] = useState(0);
  const [sessionKey, setSessionKey] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const scoredRef = useRef(false);
  const initialized = useRef(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const detailQuery = useQuery<InterviewDetail>({
    queryKey: ["interview", id],
    queryFn: () => api.get<InterviewDetail>(`/interviews/${id}`),
    retry: false,
  });

  useEffect(() => {
    if (!detailQuery.data || initialized.current) return;
    initialized.current = true;
    setChat(
      detailQuery.data.turns
        .filter((turn) => turn.speaker !== "system")
        .map((turn) => ({
          speaker: turn.speaker as ChatTurn["speaker"],
          content: turn.content,
          round: turn.round,
          followup: turn.is_followup,
        })),
    );
    setRole(detailQuery.data.role);
    setCurrentRound(detailQuery.data.current_round);
    setSeconds(detailQuery.data.duration_seconds);
  }, [detailQuery.data]);

  useEffect(() => {
    if (!id || !token || !detailQuery.isFetched || scoredRef.current) return;
    let closedByUs = false;
    setStatus("connecting");
    const socket = new WebSocket(socketUrl(id, token));
    wsRef.current = socket;

    socket.onopen = () => {
      setStatus("live");
      setError(null);
    };
    socket.onmessage = (event) => {
      let message: Record<string, unknown>;
      try {
        message = JSON.parse(event.data as string) as Record<string, unknown>;
      } catch {
        return;
      }
      const type = String(message.type ?? "");
      if (type === "session") {
        const sessionRubric = message.rubric as Rubric | undefined;
        if (sessionRubric) setRubric(sessionRubric);
        setRole(String(message.role ?? "swe"));
        setXp(Number(message.xp ?? 0));
      } else if (type === "typing") {
        setTyping(Boolean(message.on));
      } else if (type === "question") {
        const text = String(message.text ?? "");
        const round = String(message.round ?? "project");
        setCurrentRound(round);
        setIsSending(false);
        setFinished(false);
        setChat((current) => {
          const last = current[current.length - 1];
          if (last && last.speaker === "interviewer" && last.content === text) return current;
          return [
            ...current,
            {
              speaker: "interviewer",
              content: text,
              round,
              followup: Boolean(message.is_followup),
            },
          ];
        });
      } else if (type === "round_complete") {
        const next = message.next ? String(message.next) : null;
        setChat((current) => [
          ...current,
          {
            speaker: "system",
            content: message.finished
              ? t("allRoundsDone")
              : `${t("roundComplete")} → ${roundLabel(next ?? String(message.round))}`,
            round: String(message.round ?? currentRound),
          },
        ]);
        if (message.finished) {
          setFinished(true);
          setTyping(false);
          setIsSending(false);
        }
        if (next) setCurrentRound(next);
      } else if (type === "hint") {
        setHint(String(message.text ?? ""));
        setXp(Number(message.xp ?? 0));
        setHintsUsed(Number(message.hints_used ?? hintsUsed + 1));
      } else if (type === "scored") {
        scoredRef.current = true;
        setTyping(false);
        setIsSending(false);
        setFinished(true);
        setScore({
          overall: Number(message.overall ?? 0),
          criteria: (message.criteria as ScoreResult["criteria"]) ?? [],
        });
        setStatus("closed");
      } else if (type === "error") {
        setError(String(message.message ?? "Something went wrong."));
        setTyping(false);
        setIsSending(false);
      }
    };
    socket.onclose = () => {
      wsRef.current = null;
      if (!closedByUs && !scoredRef.current) setStatus("closed");
    };
    socket.onerror = () => {
      if (!scoredRef.current) setStatus("closed");
    };
    return () => {
      closedByUs = true;
      socket.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, token, detailQuery.isFetched, sessionKey]);

  useEffect(() => {
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [chat, typing]);

  function sendAnswer(event: React.FormEvent) {
    event.preventDefault();
    const text = answer.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "answer", content: text }));
    setChat((current) => [
      ...current,
      { speaker: "candidate", content: text, round: currentRound },
    ]);
    setAnswer("");
    setIsSending(true);
    setTyping(true);
  }

  function requestHint() {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "hint" }));
  }

  function finish() {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setTyping(true);
    setIsSending(true);
    wsRef.current.send(JSON.stringify({ type: "finish" }));
  }

  function reconnect() {
    setError(null);
    setStatus("connecting");
    setSessionKey((value) => value + 1);
  }

  if (!ready) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg text-sm text-muted">
        Loading…
      </div>
    );
  }

  const activeRoundIndex = ROUNDS.indexOf(currentRound as (typeof ROUNDS)[number]);
  const hasAnswers = chat.some((turn) => turn.speaker === "candidate");

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-bg">
      <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border/70 bg-surface/40 px-3 backdrop-blur-xl sm:px-5">
        <div className="flex items-center gap-2.5">
          <BrandMark className="size-8" />
          <div className="hidden sm:block">
            <p className="text-xs font-semibold">Mock interview · {role.toUpperCase()}</p>
            <p className="text-[10px] text-muted">
              Rubric {rubric?.version ?? detailQuery.data?.rubric_version ?? "v1"} ·{" "}
              {formatDuration(seconds)}
            </p>
          </div>
          <div className="flex items-center gap-1 sm:ml-3">
            {ROUNDS.map((round, index) => (
              <span
                key={round}
                title={roundLabel(round)}
                className={cn(
                  "flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide",
                  index < activeRoundIndex
                    ? "bg-success/10 text-success"
                    : index === activeRoundIndex
                      ? "bg-brand-gradient text-white"
                      : "bg-surface text-muted",
                )}
              >
                <span
                  className={cn(
                    "size-1 rounded-full",
                    index <= activeRoundIndex ? "bg-current" : "bg-muted",
                  )}
                />
                {roundLabel(round).split(" ")[0]}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="hidden items-center gap-1 rounded-lg border border-border bg-card px-2 py-1 text-[10px] font-semibold tabular-nums text-muted sm:flex">
            <Clock className="size-3" /> {formatDuration(seconds)}
          </span>
          <span className="hidden items-center gap-1 rounded-lg border border-border bg-card px-2 py-1 text-[10px] font-semibold text-primary sm:flex">
            <Zap className="size-3" /> {xp} XP
          </span>
          <LocaleSwitcher className="hidden md:flex" />
          <ThemeToggle />
          <Button asChild variant="ghost" size="sm">
            <Link href="/dashboard/interviews" aria-label={t("leave")}>
              <ArrowLeft /> <span className="hidden sm:inline">{t("leave")}</span>
            </Link>
          </Button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-h-0 flex-col">
          <div
            ref={scrollRef}
            className="flex-1 space-y-3 overflow-y-auto px-4 py-5 sm:px-6"
            aria-live="polite"
          >
            {!chat.length && !detailQuery.isError ? (
              <div className="mx-auto max-w-md space-y-3">
                <Skeleton className="h-16 w-3/4" />
                <Skeleton className="ml-auto h-20 w-4/5" />
                <Skeleton className="h-16 w-2/3" />
              </div>
            ) : null}

            {chat.map((turn, index) =>
              turn.speaker === "system" ? (
                <div key={`system-${index}`} className="flex justify-center py-2">
                  <span className="rounded-full border border-accent/20 bg-accent/5 px-3 py-1 text-[10px] font-semibold text-accent">
                    {turn.content}
                  </span>
                </div>
              ) : (
                <div
                  key={`${turn.speaker}-${index}`}
                  className={cn(
                    "flex",
                    turn.speaker === "candidate" ? "justify-end" : "justify-start",
                  )}
                >
                  <div
                    data-testid={
                      turn.speaker === "interviewer" ? "question-bubble" : "answer-bubble"
                    }
                    className={cn(
                      "max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed sm:max-w-[75%]",
                      turn.speaker === "interviewer"
                        ? "brand-border rounded-tl-md border border-border/60 bg-surface/80"
                        : "rounded-tr-md bg-brand-gradient text-white shadow-[0_10px_30px_-16px_rgba(124,92,255,0.8)]",
                    )}
                  >
                    <div className="mb-1 flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-wide opacity-70">
                      {turn.speaker === "interviewer" ? (
                        <>
                          <Mic className="size-3" />{" "}
                          {turn.followup ? "Follow-up" : roundLabel(turn.round)}
                        </>
                      ) : (
                        "You"
                      )}
                    </div>
                    {turn.content}
                  </div>
                </div>
              ),
            )}

            {typing ? (
              <div className="flex justify-start" aria-label={t("thinking")}>
                <div className="flex items-center gap-2 rounded-2xl border border-border/60 bg-surface/70 px-4 py-3">
                  <span className="flex gap-1">
                    {[0, 1, 2].map((dot) => (
                      <span
                        key={dot}
                        className="size-1.5 animate-bounce rounded-full bg-accent"
                        style={{ animationDelay: `${dot * 140}ms` }}
                      />
                    ))}
                  </span>
                  <span className="text-[10px] text-muted">{t("thinking")}…</span>
                </div>
              </div>
            ) : null}
          </div>

          {hint ? (
            <div className="mx-4 mb-2 flex items-start gap-2 rounded-xl border border-accent/25 bg-accent/5 px-3 py-2 text-[11px] text-accent sm:mx-6">
              <Lightbulb className="mt-0.5 size-3.5 shrink-0" />
              <p className="flex-1">{hint}</p>
              <button type="button" onClick={() => setHint(null)} className="text-[10px] underline">
                dismiss
              </button>
            </div>
          ) : null}

          {error ? (
            <div className="mx-4 mb-2 flex items-center justify-between gap-3 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-[11px] text-danger sm:mx-6">
              <span>{error}</span>
              <button type="button" onClick={reconnect} className="font-semibold underline">
                {tc("retry")}
              </button>
            </div>
          ) : null}

          <div className="border-t border-border/70 bg-surface/30 p-3 sm:p-4">
            {finished && !score ? (
              <div className="flex flex-col items-stretch justify-between gap-2 rounded-xl border border-primary/25 bg-primary/5 p-3 sm:flex-row sm:items-center">
                <div>
                  <p className="text-xs font-semibold">{t("allRoundsDone")}</p>
                  <p className="text-[10px] text-muted">{t("allRoundsBody")}</p>
                </div>
                <Button
                  onClick={finish}
                  loading={isSending}
                  disabled={!hasAnswers}
                  data-testid="finish-interview"
                >
                  <Square /> {isSending ? t("finishing") : t("finish")}
                </Button>
              </div>
            ) : (
              <form onSubmit={sendAnswer} className="space-y-2">
                <label htmlFor="answer" className="sr-only">
                  {t("listen")}
                </label>
                <textarea
                  id="answer"
                  data-testid="answer-input"
                  value={answer}
                  onChange={(event) => setAnswer(event.target.value.slice(0, 4000))}
                  onKeyDown={(event) => {
                    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                      sendAnswer(event);
                    }
                  }}
                  disabled={typing || Boolean(score) || status !== "live"}
                  placeholder={t("answerPlaceholder")}
                  rows={3}
                  className="w-full resize-none rounded-xl border border-border bg-card px-3.5 py-2.5 text-sm text-fg placeholder:text-muted/70 focus-visible:border-primary/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/25 disabled:opacity-60"
                />
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={requestHint}
                      disabled={status !== "live" || Boolean(score)}
                      title={t("hintLabel")}
                    >
                      <Lightbulb /> {t("hintLabel")}
                    </Button>
                    <span className="hidden items-center gap-1 text-[10px] text-muted sm:flex">
                      <Volume2 className="size-3" /> {t("voiceSoon")}
                    </span>
                    {hintsUsed > 0 ? (
                      <span className="text-[10px] text-muted">{hintsUsed} hint(s)</span>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-muted">{answer.length}/4000</span>
                    <Button
                      type="submit"
                      size="sm"
                      data-testid="send-answer"
                      disabled={!answer.trim() || typing || status !== "live" || Boolean(score)}
                      loading={isSending}
                    >
                      <Send /> {t("send")}
                    </Button>
                  </div>
                </div>
              </form>
            )}
            {status === "closed" && !score ? (
              <p className="mt-2 text-[10px] text-warning">{t("reconnecting")}</p>
            ) : null}
          </div>
        </div>

        <aside className="hidden min-h-0 flex-col overflow-y-auto border-l border-border/70 bg-surface/20 p-5 lg:flex">
          <div className="relative mx-auto flex h-44 w-44 items-center justify-center">
            <div className="absolute inset-0 rounded-full bg-primary/20 blur-2xl" />
            <div className="orb-core size-28 rounded-full" aria-hidden />
            <div className="absolute bottom-3 flex items-end gap-1" aria-hidden>
              {[0.4, 0.7, 1, 0.55, 0.85, 0.35, 0.65].map((height, index) => (
                <span
                  key={index}
                  className="wave-bar w-1 rounded-full bg-accent/80"
                  style={{ height: `${height * 26}px`, animationDelay: `${index * 120}ms` }}
                />
              ))}
            </div>
          </div>
          <div className="mt-2 text-center">
            <Badge variant="accent" className="gap-1">
              <Sparkles className="size-3" /> {typing ? t("thinking") : "Listening"}
            </Badge>
            <p className="mt-2 text-[10px] text-muted">
              {t("answered", { count: chat.filter((turn) => turn.speaker === "candidate").length })}
            </p>
          </div>

          <div className="mt-5">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">
              {t("rubricTitle")}
            </p>
            <div className="space-y-1.5">
              {(rubric?.criteria ?? []).map((criterion) => (
                <div
                  key={criterion.key}
                  className="rounded-lg border border-border/60 bg-card/60 px-2.5 py-2"
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-medium">{criterion.label}</span>
                    <span className="text-primary">{Math.round(criterion.weight * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-auto pt-4 text-[10px] leading-relaxed text-muted">
            Hints cost 5 XP. Finish all three rounds to get median-scored rubric feedback.
          </div>
        </aside>
      </div>

      {score ? (
        <div
          data-testid="scored-overlay"
          className="absolute inset-0 z-[60] flex items-center justify-center bg-black/80 px-4 backdrop-blur-md"
        >
          <div className="surface-card w-full max-w-sm p-6 text-center">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-accent">
              {t("scored")}
            </p>
            <h2 className="mt-1 font-display text-xl font-semibold">{t("finalScore")}</h2>
            <div className="mt-4 flex justify-center">
              <ReadinessRing score={score.overall} label={t("finalScore")} size={170} />
            </div>
            <div className="mt-4 space-y-1.5 text-left">
              {score.criteria.map((criterion) => (
                <div key={criterion.key} className="flex items-center justify-between text-xs">
                  <span className="text-muted">{criterion.label}</span>
                  <span className="font-semibold">{criterion.score}/10</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[10px] text-muted">{t("scoredBody")}</p>
            <Button
              className="mt-4 w-full"
              onClick={() => router.push(`/interview/${id}/feedback`)}
            >
              {t("viewFeedback")}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
