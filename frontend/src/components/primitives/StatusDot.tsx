import type { StageStatusToken } from "@/lib/status";
import { STAGE_STATUS_COLOR_VAR } from "@/lib/status";

interface StatusDotProps {
  status: StageStatusToken;
  size?: number;
}

export function StatusDot({ status, size = 7 }: StatusDotProps) {
  const color = STAGE_STATUS_COLOR_VAR[status];
  const pulse = status === "running";

  return (
    <span
      style={{
        display: "inline-block",
        width: size,
        height: size,
        borderRadius: "50%",
        background: color,
        boxShadow: `0 0 0 3px color-mix(in srgb, ${color} 16%, transparent)`,
        flexShrink: 0,
        animation: pulse ? "pulseDot 1.1s ease-in-out infinite" : undefined,
      }}
    />
  );
}
