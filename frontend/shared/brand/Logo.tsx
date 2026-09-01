import type { CSSProperties } from "react";
import logoSvgUrl from "./assets/logo.svg";
import logoPngUrl from "./assets/logo.png";

export const BRAND_NAVY = "#151B54";
export const BRAND_ORANGE = "#E5611B";
export const BRAND_LIGHT_TEXT = "#e9ecf2";

interface LogoProps {
  height?: number;
  className?: string;
  style?: CSSProperties;
  variant?: "default" | "light";
}

export function Logo({ height = 24, className, style, variant = "default" }: LogoProps) {
  const size = { height, width: "auto" } as const;
  return (
    <picture
      role="img"
      aria-label="PropAura"
      className={className}
      style={{ display: "inline-block", ...size, ...style }}
    >
      <source type="image/svg+xml" srcSet={logoSvgUrl} />
      <img
        src={logoPngUrl}
        alt="PropAura"
        draggable={false}
        style={{
          display: "block",
          ...size,
          filter: variant === "light" ? "brightness(0) invert(1)" : undefined,
        }}
      />
    </picture>
  );
}

export default Logo;