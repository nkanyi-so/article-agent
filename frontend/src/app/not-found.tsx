import Link from "next/link";

export default function NotFound() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        gap: 16,
        padding: 32,
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: 48,
          fontWeight: 700,
          fontFamily: "var(--font-mono), monospace",
          color: "var(--text3)",
        }}
      >
        404
      </div>
      <p style={{ fontSize: 16, color: "var(--text2)", maxWidth: 360 }}>
        There is nothing at this address.
      </p>
      <Link
        href="/"
        style={{
          display: "inline-flex",
          alignItems: "center",
          padding: "8px 16px",
          borderRadius: 9,
          border: "1px solid var(--border2)",
          background: "var(--surface2)",
          color: "var(--text)",
          fontSize: 13,
          fontWeight: 600,
          textDecoration: "none",
        }}
      >
        ← Back to the transcripts
      </Link>
    </div>
  );
}
