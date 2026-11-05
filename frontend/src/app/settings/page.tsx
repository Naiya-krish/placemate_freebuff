"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  Database,
  Languages,
  LogOut,
  Moon,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { AppShell, FullPageLoader, PageHeading } from "@/components/app-shell";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { ThemeToggle, useTheme } from "@/components/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Input, Label } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { api, ApiError, logout } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useRequireAuth } from "@/hooks/use-session";
import type { Usage, User } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function SettingsPage() {
  const t = useTranslations("settings");
  const tc = useTranslations("common");
  const router = useRouter();
  const { user, ready } = useRequireAuth();
  const { setUser, clear } = useAuthStore();
  const { theme } = useTheme();
  const [share, setShare] = useState(user?.consent_share_analytics ?? false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  useEffect(() => {
    setShare(user?.consent_share_analytics ?? false);
  }, [user?.consent_share_analytics]);

  const usageQuery = useQuery<Usage>({
    queryKey: ["usage"],
    queryFn: () => api.get<Usage>("/usage/me"),
    retry: false,
  });

  const consentMutation = useMutation({
    mutationFn: (value: boolean) => api.post<User>("/auth/consent", { share_analytics: value }),
    onSuccess: (updated) => {
      setUser(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : "Could not save that preference."),
  });

  const deleteMutation = useMutation({
    mutationFn: () =>
      api.delete<void>("/account", {
        confirm,
        password: password || undefined,
      }),
    onSuccess: () => {
      clear();
      router.replace("/");
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Deletion failed."),
  });

  async function signOut() {
    await logout();
    router.replace("/login");
  }

  if (!ready || !user) return <FullPageLoader label="Opening settings" />;

  return (
    <AppShell user={user}>
      <PageHeading
        eyebrow={user.role.replace("_", " ")}
        title={t("title")}
        subtitle={t("subtitle")}
        actions={
          <Button variant="secondary" onClick={signOut}>
            <LogOut /> {tc("signOut")}
          </Button>
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

      <div className="grid gap-4 lg:grid-cols-12">
        <Card className="lg:col-span-5">
          <CardHeader>
            <div>
              <CardTitle>{t("account")}</CardTitle>
              <CardDescription>{user.email}</CardDescription>
            </div>
            <Badge variant="accent" className="capitalize">
              {user.role}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between border-b border-border/60 py-1.5">
              <span className="text-muted">Name</span>
              <span className="font-medium">{user.name}</span>
            </div>
            <div className="flex justify-between border-b border-border/60 py-1.5">
              <span className="text-muted">College</span>
              <span className="font-medium">{user.college_name ?? "—"}</span>
            </div>
            <div className="flex justify-between border-b border-border/60 py-1.5">
              <span className="text-muted">Branch</span>
              <span className="font-medium">{user.branch ?? "—"}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-muted">Member since</span>
              <span className="font-medium">{formatDate(user.created_at)}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-7">
          <CardHeader>
            <div>
              <CardTitle>{t("privacy")}</CardTitle>
              <CardDescription>{t("shareBody")}</CardDescription>
            </div>
            <ShieldCheck className="size-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="flex items-start justify-between gap-4 rounded-xl border border-border bg-surface/40 p-4">
              <div>
                <p className="text-xs font-semibold">{t("shareTitle")}</p>
                <p className="mt-1 text-[11px] leading-relaxed text-muted">
                  Off by default. Aggregate analytics always include anonymised data.
                </p>
                {saved ? (
                  <p className="mt-2 text-[11px] text-success">{t("consentSaved")}</p>
                ) : null}
              </div>
              <Switch
                checked={share}
                onCheckedChange={(value) => {
                  setShare(value);
                  consentMutation.mutate(value);
                }}
                label={t("shareTitle")}
              />
            </div>
            <div className="mt-4 rounded-xl border border-border/70 bg-surface/30 p-4">
              <p className="flex items-center gap-2 text-xs font-semibold">
                <Database className="size-3.5 text-accent" /> {t("retention")}
              </p>
              <p className="mt-1.5 text-[11px] leading-relaxed text-muted">{t("retentionBody")}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-5">
          <CardHeader>
            <div>
              <CardTitle>{t("usage")}</CardTitle>
              <CardDescription>{usageQuery.data?.month ?? "Current month"}</CardDescription>
            </div>
            <Sparkles className="size-4 text-accent" />
          </CardHeader>
          <CardContent>
            {usageQuery.data ? (
              <>
                <div className="flex items-end justify-between">
                  <p className="font-display text-3xl font-semibold">
                    {usageQuery.data.percent_used}%
                  </p>
                  <p className="text-xs text-muted">
                    {formatCurrency(usageQuery.data.cost_usd)} /{" "}
                    {formatCurrency(usageQuery.data.budget_usd)}
                  </p>
                </div>
                <Progress value={usageQuery.data.percent_used} className="mt-3 h-2" />
                <p className="mt-2 text-[11px] text-muted">
                  {t("usageBody")} · {usageQuery.data.tokens.toLocaleString()} tokens used.
                </p>
              </>
            ) : (
              <p className="py-4 text-xs text-muted">Usage is unavailable right now.</p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-7">
          <CardHeader>
            <div>
              <CardTitle>
                {t("languageTitle")} & {t("themeTitle")}
              </CardTitle>
              <CardDescription>{t("languageBody")}</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between rounded-xl border border-border bg-surface/40 p-3">
              <div className="flex items-center gap-2 text-xs font-semibold">
                <Languages className="size-4 text-primary" /> {t("languageTitle")}
              </div>
              <LocaleSwitcher />
            </div>
            <div className="flex items-center justify-between rounded-xl border border-border bg-surface/40 p-3">
              <div className="flex items-center gap-2 text-xs font-semibold">
                <Moon className="size-4 text-primary" /> {t("themeTitle")}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] capitalize text-muted">{theme}</span>
                <ThemeToggle />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-danger/25 lg:col-span-12">
          <CardHeader>
            <div>
              <CardTitle className="text-danger">{t("dangerZone")}</CardTitle>
              <CardDescription>{t("deleteBody")}</CardDescription>
            </div>
            <AlertTriangle className="size-4 text-danger" />
          </CardHeader>
          <CardContent>
            <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
              <DialogTrigger asChild>
                <Button variant="danger">
                  <Trash2 /> {t("deleteTitle")}
                </Button>
              </DialogTrigger>
              <DialogContent title={t("deleteTitle")} description={t("deleteBody")}>
                <div className="space-y-4">
                  {user && user.email.endsWith("@placemate.dev") ? null : (
                    <div>
                      <Label htmlFor="delete-password">{t("passwordRequired")}</Label>
                      <Input
                        id="delete-password"
                        type="password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        autoComplete="current-password"
                      />
                    </div>
                  )}
                  <div>
                    <Label htmlFor="delete-confirm">{t("deleteConfirm")}</Label>
                    <Input
                      id="delete-confirm"
                      value={confirm}
                      onChange={(event) => setConfirm(event.target.value.toUpperCase())}
                      placeholder="DELETE"
                    />
                  </div>
                  <Button
                    variant="danger"
                    className="w-full"
                    disabled={confirm !== "DELETE" || deleteMutation.isPending}
                    loading={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate()}
                  >
                    {deleteMutation.isPending ? t("deleting") : t("deleteButton")}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
