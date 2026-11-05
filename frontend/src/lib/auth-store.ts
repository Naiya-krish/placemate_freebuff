"use client";

import { create } from "zustand";
import type { User } from "@/lib/types";

interface AuthState {
  accessToken: string | null;
  user: User | null;
  ready: boolean;
  setSession: (accessToken: string, user: User) => void;
  setUser: (user: User) => void;
  setReady: (ready: boolean) => void;
  clear: () => void;
}

/**
 * Access tokens live in memory only (never localStorage) so an XSS cannot exfiltrate a
 * long-lived credential. The HttpOnly refresh cookie restores the session on reload.
 */
export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  ready: false,
  setSession: (accessToken, user) => set({ accessToken, user, ready: true }),
  setUser: (user) => set({ user }),
  setReady: (ready) => set({ ready }),
  clear: () => set({ accessToken: null, user: null, ready: true }),
}));
