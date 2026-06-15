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
        This page doesn&apos;t exist, or the run you&apos;re looking for was cleared when the
        server restarted (the store is in-memory for now).
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
        ← New article
      </Link>
    </div>
  );
}
