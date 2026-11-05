import type { Metadata, Viewport } from "next";
import { cookies } from "next/headers";
import "./globals.css";
import { Providers } from "@/components/providers";
import en from "@/messages/en.json";
import hi from "@/messages/hi.json";

const messages = { en, hi };

export const metadata: Metadata = {
  title: {
    default: "PlaceMate — placement preparation that starts with your resume",
    template: "%s · PlaceMate",
  },
  description:
    "Score your resume, get truthful job-tailored edits, and rehearse resume-grounded mock interviews with a visible rubric. Aggregate-only readiness analytics for placement cells.",
  applicationName: "PlaceMate",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [{ url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }],
    apple: [{ url: "/icons/icon-192.png" }],
  },
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "PlaceMate" },
  openGraph: {
    title: "PlaceMate — walk into placement season ready",
    description:
      "Resume scoring, truthful tailoring edits and rubric-scored mock interviews grounded in your own projects.",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#07070d" },
    { media: "(prefers-color-scheme: light)", color: "#f7f7fb" },
  ],
};

const themeScript = `
try {
  var stored = localStorage.getItem('placemate-theme');
  if (stored === 'light') document.documentElement.classList.add('light');
  document.documentElement.dataset.theme = stored === 'light' ? 'light' : 'dark';
} catch (e) {}
`;

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  const locale = cookieStore.get("placemate_locale")?.value === "hi" ? "hi" : "en";
  return (
    <html lang={locale} className="dark" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap"
        />
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <link rel="manifest" href="/manifest.webmanifest" />
      </head>
      <body>
        <Providers locale={locale} messages={messages[locale] as never}>
          {children}
        </Providers>
      </body>
    </html>
  );
}
