import type { Source } from "@/lib/run-types";

interface ReferencesListProps {
  sources: Source[];
}

export function ReferencesList({ sources }: ReferencesListProps) {
  if (sources.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div
        style={{
          fontSize: 10,
          fontWeight: 600,
          fontFamily: "var(--font-mono), monospace",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "var(--text3)",
          marginBottom: 4,
        }}
      >
        References
      </div>
      {sources.map((source, i) => (
        <div key={source.id} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
          <span
            style={{
              fontSize: 11,
              fontFamily: "var(--font-mono), monospace",
              color: "var(--text3)",
              minWidth: 20,
              paddingTop: 2,
            }}
          >
            [{i + 1}]
          </span>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {source.url ? (
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  fontSize: 13,
                  color: "var(--accent)",
                  textDecoration: "none",
                  fontWeight: 500,
                }}
              >
                {source.title ?? source.url}
              </a>
            ) : (
              <span style={{ fontSize: 13, color: "var(--text2)", fontWeight: 500 }}>
                {source.title ?? source.id}
              </span>
            )}
            {source.snippet && (
              <p
                style={{
                  fontSize: 12,
                  color: "var(--text3)",
                  margin: 0,
                  lineHeight: 1.5,
                  display: "-webkit-box",
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: "vertical",
                  overflow: "hidden",
                }}
              >
                {source.snippet}
              </p>
            )}
            <span
              style={{
                fontSize: 10,
                fontFamily: "var(--font-mono), monospace",
                color: "var(--text3)",
              }}
            >
              {source.kind} · {source.id}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
