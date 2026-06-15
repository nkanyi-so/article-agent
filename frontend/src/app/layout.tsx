import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeScript } from "@/components/shell/ThemeScript";
import { TopBar } from "@/components/shell/TopBar";
import { Sidebar } from "@/components/shell/Sidebar";
import { api } from "@/lib/api";
import type { Run } from "@/lib/run-types";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Bylined — Grounded articles from real sources",
  description:
    "Enter a person's name. Bylined researches, writes, and fact-checks a grounded article — every claim traced to a real source.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Fetch run history for the sidebar. Fails gracefully (backend may be down
  // at dev start or after a restart which clears the in-memory store).
  let runs: Run[] = [];
  try {
    runs = await api.listRuns();
    // Most-recent first.
    runs = runs.slice().sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  } catch {
    // Sidebar just renders empty.
  }

  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full`}
    >
      <head>
        <ThemeScript />
      </head>
      <body
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          background: "var(--bg)",
          color: "var(--text)",
        }}
      >
        <TopBar />
        <div
          style={{
            display: "flex",
            flex: 1,
            overflow: "hidden",
            height: "calc(100vh - 56px)",
          }}
        >
          <Sidebar runs={runs} />
          <main
            style={{
              flex: 1,
              overflowY: "auto",
              background: "var(--bg)",
            }}
          >
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
