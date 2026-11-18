import type { StageStatusToken } from "@/lib/status";
import { STAGE_STATUS_COLOR_VAR, STAGE_STATUS_LABEL } from "@/lib/status";
import { StatusDot } from "./StatusDot";

interface StatusPillProps {
  status: StageStatusToken;
}

export function StatusPill({ status }: StatusPillProps) {
  const color = STAGE_STATUS_COLOR_VAR[status];
  const label = STAGE_STATUS_LABEL[status];

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "3px 10px 3px 8px",
        borderRadius: 999,
        border: `1px solid color-mix(in srgb, ${color} 26%, transparent)`,
        background: `color-mix(in srgb, ${color} 12%, transparent)`,
        color,
        fontSize: 11,
        fontWeight: 600,
        fontFamily: "inherit",
        whiteSpace: "nowrap",
      }}
    >
      <StatusDot status={status} size={6} />
      {label}
    </span>
  );
}
