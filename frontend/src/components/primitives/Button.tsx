import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: ReactNode;
}

const VARIANT_STYLES: Record<ButtonVariant, React.CSSProperties> = {
  primary: {
    background: "var(--accent)",
    color: "var(--accentText)",
    border: `1px solid color-mix(in srgb, var(--accent) 65%, #000)`,
  },
  secondary: {
    background: "var(--surface2)",
    color: "var(--text)",
    border: "1px solid var(--border2)",
  },
  ghost: {
    background: "transparent",
    color: "var(--text2)",
    border: "1px solid transparent",
  },
  danger: {
    background: "color-mix(in srgb, var(--fail) 10%, transparent)",
    color: "var(--fail)",
    border: "1px solid color-mix(in srgb, var(--fail) 26%, transparent)",
  },
};

export function Button({
  variant = "secondary",
  children,
  disabled,
  style,
  ...rest
}: ButtonProps) {
  const variantStyle = VARIANT_STYLES[variant];

  return (
    <button
      disabled={disabled}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "8px 14px",
        borderRadius: 9,
        fontSize: 13,
        fontWeight: 600,
        fontFamily: "inherit",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.45 : 1,
        transition: "opacity 0.12s, background 0.12s",
        whiteSpace: "nowrap",
        ...variantStyle,
        ...(style ?? {}),
      }}
      {...rest}
    >
      {children}
    </button>
  );
}
