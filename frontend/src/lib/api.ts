"use client";

import { useAuthStore } from "@/lib/auth-store";
import type { AuthResponse, User } from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(
  /\/$/,
  "",
);
export const WS_URL = (process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1").replace(
  /\/$/,
  "",
);
export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = "error") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

let refreshInFlight: Promise<boolean> | null = null;

export function refreshSession(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      });
      if (!response.ok) return false;
      const data = (await response.json()) as AuthResponse;
      useAuthStore.getState().setSession(data.access_token, data.user);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

export async function fetchCurrentUser(): Promise<User | null> {
  try {
    return await api.get<User>("/auth/me");
  } catch {
    return null;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  auth?: boolean;
  raw?: boolean;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, auth = true, raw = false, headers, ...rest } = options;
  return request<T>(path, { ...rest, headers, body, auth, raw }, true);
}

async function request<T>(path: string, options: RequestOptions, retry: boolean): Promise<T> {
  const token = useAuthStore.getState().accessToken;
  const headers = new Headers(options.headers);
  if (options.auth !== false && token) headers.set("Authorization", `Bearer ${token}`);
  let body: BodyInit | undefined;
  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      body,
      credentials: "include",
    });
  } catch {
    throw new ApiError(
      "Cannot reach the PlaceMate API. Check that the backend is running.",
      0,
      "network_error",
    );
  }

  if (response.status === 401 && retry && !path.startsWith("/auth/")) {
    const refreshed = await refreshSession();
    if (refreshed) return request<T>(path, options, false);
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    let code = "error";
    try {
      const payload = (await response.json()) as { detail?: string; code?: string };
      detail = payload.detail || detail;
      code = payload.code || code;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(detail, response.status, code);
  }

  if (response.status === 204) return undefined as T;
  if (options.raw) return (await response.blob()) as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  post: <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: "DELETE", body }),
  upload: <T>(path: string, form: FormData) => apiFetch<T>(path, { method: "POST", body: form }),
  blob: (path: string) => apiFetch<Blob>(path, { raw: true }),
};

export async function login(email: string, password: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
}

export async function demoLogin(role: "student" | "officer" | "admin"): Promise<AuthResponse> {
  return apiFetch<AuthResponse>(`/auth/demo-login?role=${role}`, {
    method: "POST",
    auth: false,
  });
}

export async function logout(): Promise<void> {
  try {
    await apiFetch<void>("/auth/logout", { method: "POST", auth: false });
  } finally {
    useAuthStore.getState().clear();
  }
}
