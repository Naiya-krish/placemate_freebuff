"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider, type AbstractIntlMessages } from "next-intl";
import { ThemeProvider } from "@/components/theme-provider";
import { useSessionBootstrap } from "@/hooks/use-session";
import { PwaRegister } from "@/components/pwa-register";

function SessionBootstrap() {
  useSessionBootstrap();
  return null;
}

export function Providers({
  children,
  locale,
  messages,
}: {
  children: React.ReactNode;
  locale: string;
  messages: AbstractIntlMessages;
}) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <NextIntlClientProvider locale={locale} messages={messages} timeZone="Asia/Kolkata">
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <SessionBootstrap />
          {children}
          <PwaRegister />
        </QueryClientProvider>
      </ThemeProvider>
    </NextIntlClientProvider>
  );
}
