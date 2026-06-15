/**
 * /design-system — standalone portfolio page.
 *
 * NOT linked from the product navigation — accessible directly at /design-system.
 * Showcases the full token system, component primitives, and status/eval states
 * in both dark and light themes.
 */
"use client";

import { StatusPill } from "@/components/primitives/StatusPill";
import { StatusDot } from "@/components/primitives/StatusDot";
import { EvalPill } from "@/components/primitives/EvalPill";
import { Button } from "@/components/primitives/Button";
import { Badge } from "@/components/primitives/Badge";
import { Chip } from "@/components/primitives/Chip";
import { StatCard } from "@/components/primitives/StatCard";
import { CodeWell } from "@/components/primitives/CodeWell";
import { Spinner } from "@/components/primitives/Spinner";
import { SegmentedControl } from "@/components/primitives/SegmentedControl";
import { ThemeToggle } from "@/components/shell/ThemeToggle";
import type { StageStatusToken, EvalPillVerdict } from "@/lib/status";

// ─── Section wrapper ────────────────────────────────────────────────────────

function Section({
  title,
  sub,
  children,
}: {
  title: string;
  sub?: string;
  children: React.ReactNode;
}) {
  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <h2
          style={{
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            color: "var(--text3)",
            margin: 0,
          }}
        >
          {title}
        </h2>
        {sub && (
          <p style={{ fontSize: 12, color: "var(--text3)", margin: "4px 0 0" }}>
            {sub}
          </p>
        )}
      </div>
      {children}
    </section>
  );
}

// ─── Color swatch ────────────────────────────────────────────────────────────

function Swatch({
  varName,
  label,
}: {
  varName: string;
  label: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        alignItems: "center",
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: 10,
          background: `var(${varName})`,
          border: "1px solid color-mix(in srgb, var(--text) 8%, transparent)",
          flexShrink: 0,
        }}
      />
      <span
        style={{
          fontSize: 10,
          fontFamily: "var(--font-mono), monospace",
          color: "var(--text3)",
          textAlign: "center",
          letterSpacing: "0.02em",
        }}
      >
        {varName}
        <br />
        <span style={{ color: "var(--text2)" }}>{label}</span>
      </span>
    </div>
  );
}

// ─── Row helper ──────────────────────────────────────────────────────────────

function Row({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
      {children}
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

const STATUS_TOKENS: StageStatusToken[] = ["pending", "running", "ok", "error"];
const EVAL_VERDICTS: EvalPillVerdict[] = ["pass", "warn", "fail"];

const EXAMPLE_JSON = {
  name: "Sam Altman",
  organization: "OpenAI",
  role: "CEO",
};

export default function DesignSystemPage() {
  return (
    <div
      style={{
        maxWidth: 900,
        margin: "0 auto",
        padding: "60px 28px 120px",
        display: "flex",
        flexDirection: "column",
        gap: 56,
      }}
    >
      {/* ── Header ── */}
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 16,
          }}
        >
          <div>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "3px 10px",
                borderRadius: 999,
                border: "1px solid var(--border2)",
                background: "var(--surface)",
                fontSize: 10,
                fontWeight: 600,
                fontFamily: "var(--font-mono), monospace",
                letterSpacing: "0.06em",
                color: "var(--text3)",
                marginBottom: 16,
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "var(--accent)",
                  display: "inline-block",
                }}
              />
              Design System · Portfolio
            </div>
            <h1
              style={{
                fontSize: 32,
                fontWeight: 700,
                letterSpacing: "-0.025em",
                color: "var(--text)",
                margin: 0,
              }}
            >
              Bylined Design System
            </h1>
            <p
              style={{
                fontSize: 14,
                color: "var(--text2)",
                marginTop: 8,
                lineHeight: 1.6,
              }}
            >
              Tokens, primitives, and component states for the Bylined article
              pipeline UI. Not linked from the product — this is a reference and
              portfolio page.
            </p>
          </div>
          <ThemeToggle />
        </div>
      </div>

      {/* ── Color tokens ── */}
      <Section
        title="Color tokens"
        sub="All surfaces, text, borders, and semantic colours. Switch theme above to verify the full palette."
      >
        <div>
          <p
            style={{
              fontSize: 11,
              fontWeight: 600,
              fontFamily: "var(--font-mono), monospace",
              color: "var(--text3)",
              marginBottom: 12,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Surfaces
          </p>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <Swatch varName="--bg" label="background" />
            <Swatch varName="--bgSub" label="bg-sub" />
            <Swatch varName="--surface" label="surface" />
            <Swatch varName="--surface2" label="surface-2" />
            <Swatch varName="--inset" label="inset" />
          </div>
        </div>

        <div style={{ marginTop: 20 }}>
          <p
            style={{
              fontSize: 11,
              fontWeight: 600,
              fontFamily: "var(--font-mono), monospace",
              color: "var(--text3)",
              marginBottom: 12,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Text
          </p>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <Swatch varName="--text" label="primary" />
            <Swatch varName="--text2" label="secondary" />
            <Swatch varName="--text3" label="muted" />
          </div>
        </div>

        <div style={{ marginTop: 20 }}>
          <p
            style={{
              fontSize: 11,
              fontWeight: 600,
              fontFamily: "var(--font-mono), monospace",
              color: "var(--text3)",
              marginBottom: 12,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Borders
          </p>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <Swatch varName="--border" label="default" />
            <Swatch varName="--border2" label="raised" />
          </div>
        </div>

        <div style={{ marginTop: 20 }}>
          <p
            style={{
              fontSize: 11,
              fontWeight: 600,
              fontFamily: "var(--font-mono), monospace",
              color: "var(--text3)",
              marginBottom: 12,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Semantic
          </p>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <Swatch varName="--accent" label="accent/cta" />
            <Swatch varName="--run" label="running" />
            <Swatch varName="--pass" label="pass/ok" />
            <Swatch varName="--fail" label="fail/error" />
            <Swatch varName="--err" label="warn/err" />
          </div>
        </div>
      </Section>

      {/* ── Typography ── */}
      <Section title="Typography">
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <p style={{ fontSize: 11, color: "var(--text3)", margin: "0 0 4px", fontFamily: "var(--font-mono), monospace" }}>
              display / 28px · weight 600
            </p>
            <p style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em", color: "var(--text)", margin: 0 }}>
              Sam Altman, CEO of OpenAI
            </p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: "var(--text3)", margin: "0 0 4px", fontFamily: "var(--font-mono), monospace" }}>
              heading / 20px · weight 700
            </p>
            <p style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text)", margin: 0 }}>
              How Claude Changes Product Writing
            </p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: "var(--text3)", margin: "0 0 4px", fontFamily: "var(--font-mono), monospace" }}>
              body / 15px · 1.7 leading
            </p>
            <p style={{ fontSize: 15, lineHeight: 1.7, color: "var(--text)", margin: 0, maxWidth: 560 }}>
              Every claim in a Bylined article is grounded against a real source. If the pipeline
              can't support a claim, it either removes it or flags it — no hallucination, no
              confident invention.
            </p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: "var(--text3)", margin: "0 0 4px", fontFamily: "var(--font-mono), monospace" }}>
              caption / 12px · text2
            </p>
            <p style={{ fontSize: 12, color: "var(--text2)", lineHeight: 1.5, margin: 0 }}>
              4 stages · 12.3 s · 3/3 evals passed
            </p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: "var(--text3)", margin: "0 0 4px", fontFamily: "var(--font-mono), monospace" }}>
              label / 10px · mono · uppercase
            </p>
            <p
              style={{
                fontSize: 10,
                fontFamily: "var(--font-mono), monospace",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "var(--text3)",
                margin: 0,
              }}
            >
              Stage · Duration · Eval score
            </p>
          </div>
        </div>
      </Section>

      {/* ── Status pills ── */}
      <Section title="Status pills" sub="Stage lifecycle: pending → running → ok / error">
        <Row>
          {STATUS_TOKENS.map((s) => (
            <StatusPill key={s} status={s} />
          ))}
        </Row>
        <div>
          <p
            style={{
              fontSize: 11,
              color: "var(--text3)",
              margin: "0 0 8px",
              fontFamily: "var(--font-mono), monospace",
            }}
          >
            StatusDot — standalone (6px, 8px, 10px)
          </p>
          <Row>
            {STATUS_TOKENS.map((s) => (
              <div key={s} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <StatusDot status={s} size={6} />
                <StatusDot status={s} size={8} />
                <StatusDot status={s} size={10} />
                <span style={{ fontSize: 11, color: "var(--text3)", fontFamily: "var(--font-mono), monospace" }}>
                  {s}
                </span>
              </div>
            ))}
          </Row>
        </div>
      </Section>

      {/* ── Eval pills ── */}
      <Section title="Eval pills" sub="LLM judge verdicts: pass / warn (degraded) / fail">
        <Row>
          {EVAL_VERDICTS.map((v) => (
            <EvalPill key={v} verdict={v} />
          ))}
        </Row>
        <div>
          <p
            style={{
              fontSize: 11,
              color: "var(--text3)",
              margin: "0 0 8px",
              fontFamily: "var(--font-mono), monospace",
            }}
          >
            mini mode (used inline in stage rows)
          </p>
          <Row>
            {EVAL_VERDICTS.map((v) => (
              <EvalPill key={v} verdict={v} mini />
            ))}
          </Row>
        </div>
      </Section>

      {/* ── Buttons ── */}
      <Section title="Buttons">
        <Row>
          <Button variant="primary">Start article</Button>
          <Button variant="secondary">Run evals</Button>
          <Button variant="ghost">Cancel</Button>
          <Button variant="danger">Delete run</Button>
        </Row>
        <Row>
          <Button variant="primary" disabled>
            Start article
          </Button>
          <Button variant="secondary" disabled>
            Run evals
          </Button>
        </Row>
        <Row>
          <Button variant="primary">
            <Spinner size={12} color="currentColor" />
            Generating…
          </Button>
        </Row>
      </Section>

      {/* ── Badges ── */}
      <Section title="Badges">
        <Row>
          <Badge>run_01jz</Badge>
          <Badge accent>LIVE</Badge>
          <Badge>4 stages</Badge>
          <Badge accent>12.3 s</Badge>
        </Row>
      </Section>

      {/* ── Chips ── */}
      <Section title="Chips" sub="Used in RunHeader summary row">
        <Row>
          <Chip label="stages" value="4" />
          <Chip label="duration" value="12.3 s" />
          <Chip label="evals" value="3 / 3" />
          <Chip label="score" value="0.92" />
        </Row>
      </Section>

      {/* ── StatCard ── */}
      <Section title="StatCard" sub="Compact metric tile used in eval breakdowns">
        <Row>
          <StatCard label="Groundedness" value="0.92" />
          <StatCard label="Entity resolution" value="PASS" />
          <StatCard label="Angle support" value="WARN" />
          <StatCard label="Duration" value="12.3 s" />
        </Row>
      </Section>

      {/* ── Segmented control ── */}
      <Section title="Segmented control" sub="Article / Trace toggle inside RunView">
        <SegmentedControlDemo />
      </Section>

      {/* ── Spinner ── */}
      <Section title="Spinner">
        <Row>
          <Spinner size={14} />
          <Spinner size={18} />
          <Spinner size={24} />
          <Spinner size={32} />
        </Row>
      </Section>

      {/* ── CodeWell ── */}
      <Section title="CodeWell" sub="Pretty-printed JSON for stage inputs / outputs">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <CodeWell label="Input" value={EXAMPLE_JSON} />
          <CodeWell
            label="Output"
            value={{
              name: "Sam Altman",
              organization: "OpenAI",
              linkedin_url: "https://linkedin.com/in/sama",
              title: "CEO",
              bio_snippet: "Sam Altman is the CEO of OpenAI, the company behind ChatGPT and GPT-4.",
            }}
          />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <CodeWell label="Empty" value={null} />
          <CodeWell label="Error" value="Could not resolve entity: ambiguous match" />
        </div>
      </Section>

      {/* ── Shadow ── */}
      <Section title="Elevation" sub="--shadow token (adapts per theme)">
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          {(["surface", "surface2"] as const).map((s) => (
            <div
              key={s}
              style={{
                width: 160,
                height: 80,
                borderRadius: 12,
                background: `var(--${s})`,
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 11,
                fontFamily: "var(--font-mono), monospace",
                color: "var(--text3)",
              }}
            >
              --{s}
            </div>
          ))}
        </div>
      </Section>

      {/* ── Footer ── */}
      <div
        style={{
          paddingTop: 24,
          borderTop: "1px solid var(--border)",
          fontSize: 11,
          color: "var(--text3)",
          fontFamily: "var(--font-mono), monospace",
        }}
      >
        Bylined design system · article-agent · not linked from product nav
      </div>
    </div>
  );
}

// ─── Interactive segmented-control demo ──────────────────────────────────────

function SegmentedControlDemo() {
  type Tab = "article" | "trace";
  const [tab, setTab] = React.useState<Tab>("article");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <SegmentedControl
        options={[
          { value: "article" as Tab, label: "Article" },
          { value: "trace" as Tab, label: "Trace" },
        ]}
        value={tab}
        onChange={setTab}
      />
      <p style={{ fontSize: 12, color: "var(--text3)", margin: 0, fontFamily: "var(--font-mono), monospace" }}>
        active: {tab}
      </p>
    </div>
  );
}

// Hoist React import for the inline component
import React from "react";
