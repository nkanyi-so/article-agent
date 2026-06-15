"use client";

interface Option<T extends string> {
  value: T;
  label: string;
}

interface SegmentedControlProps<T extends string> {
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  disabled = false,
}: SegmentedControlProps<T>) {
  return (
    <div
      style={{
        display: "inline-flex",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 10,
        padding: "3px",
        gap: "2px",
        opacity: disabled ? 0.5 : 1,
        pointerEvents: disabled ? "none" : undefined,
      }}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            style={{
              padding: "4px 12px",
              borderRadius: 7,
              border: active ? "1px solid var(--border2)" : "1px solid transparent",
              background: active ? "var(--surface2)" : "transparent",
              color: active ? "var(--text)" : "var(--text3)",
              fontSize: 13,
              fontWeight: 500,
              fontFamily: "inherit",
              cursor: "pointer",
              transition: "background 0.1s, color 0.1s",
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
