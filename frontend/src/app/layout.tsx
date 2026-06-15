import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeScript } from "@/components/shell/ThemeScript";
import { TopBar } from "@/components/shell/TopBar";
import { Sidebar } from "@/components/shell/Sidebar";
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
  title: "Article Agent — Grounded articles from real sources",
  description:
    "Enter a person's name. Article Agent researches, writes, and fact-checks a grounded article — every claim traced to a real source.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
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
          height: "100vh",
          overflow: "hidden",
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
            minHeight: 0,
          }}
        >
          <Sidebar />
          <main
            style={{
              flex: 1,
              minWidth: 0,
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
