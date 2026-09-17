// components/auth/BrandLogo.tsx
import type { LogoProp } from "./types";

interface BrandLogoProps {
  logo?: LogoProp;
  brandName?: string;
  size?: number;
}

/**
 * Renders whatever the consumer passed as `logo`:
 * - string  -> treated as an image path (svg/png/jpg all work through <img>)
 * - ReactNode -> rendered as-is (inline SVG, styled text, custom component)
 * - undefined -> a neutral placeholder mark using the first letter of brandName
 */
export function BrandLogo({ logo, brandName = "Your Product", size = 36 }: BrandLogoProps) {
  if (typeof logo === "string") {
    return (
      <img
        src={logo}
        alt={brandName}
        style={{ height: size, width: "auto" }}
        className="object-contain"
      />
    );
  }

  if (logo) {
    return <div style={{ height: size }}>{logo}</div>;
  }

  return (
    <div
      style={{ height: size, width: size }}
      className="flex items-center justify-center rounded-lg bg-primary text-primary-foreground font-semibold"
    >
      {brandName.charAt(0).toUpperCase()}
    </div>
  );
}
