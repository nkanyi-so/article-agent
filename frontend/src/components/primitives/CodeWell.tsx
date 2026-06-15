import { prettyJson } from "@/lib/format";

interface CodeWellProps {
  label?: string;
  value: unknown;
  maxHeight?: number;
}

export function CodeWell({ label, value, maxHeight = 200 }: CodeWellProps) {
  const text = prettyJson(value);

  return (
    <div>
      {label && (
        <div
          style={{
            fontSize: 10,
            fontWeight: 600,
            fontFamily: "var(--font-mono), monospace",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--text3)",
            marginBottom: 6,
          }}
        >
          {label}
        </div>
      )}
      <pre
        style={{
          margin: 0,
          padding: "12px 14px",
          borderRadius: 9,
          background: "var(--inset)",
          border: "1px solid var(--border)",
          color: "var(--text2)",
          fontSize: 12,
          fontFamily: "var(--font-mono), monospace",
          lineHeight: 1.65,
          maxHeight,
          overflowY: "auto",
          overflowX: "auto",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {text || <span style={{ color: "var(--text3)" }}>—</span>}
      </pre>
    </div>
  );
}
