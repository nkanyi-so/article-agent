interface SpinnerProps {
  size?: number;
  color?: string;
}

export function Spinner({ size = 16, color = "var(--accent)" }: SpinnerProps) {
  return (
    <span
      aria-label="Loading"
      style={{
        display: "inline-block",
        width: size,
        height: size,
        borderRadius: "50%",
        border: `2px solid color-mix(in srgb, ${color} 20%, transparent)`,
        borderTopColor: color,
        animation: "spin 0.7s linear infinite",
        flexShrink: 0,
      }}
    />
  );
}
