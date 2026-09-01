import "./BrandLoading.css";
import logoSvgUrl from "../brand/assets/logo.svg";
import logoPngUrl from "../brand/assets/logo.png";

export type BrandWaveSize = "sm" | "md" | "lg";

interface BrandWaveProps {
  label?: string;
  size?: BrandWaveSize;
  stacked?: boolean;
  className?: string;
}

const SIZES: Record<BrandWaveSize, number> = { lg: 48, md: 16, sm: 13 };

export function BrandWave({ label, size = "md", stacked = false, className = "" }: BrandWaveProps) {
  return (
    <span
      className={`brand-wave ${stacked ? "brand-wave--stacked" : "brand-wave--row"} ${className}`}
      role="status"
      aria-label="PropAura loading"
    >
      <picture className="brand-wave-logo">
        <source type="image/svg+xml" srcSet={logoSvgUrl} />
        <img
          src={logoPngUrl}
          alt="PropAura"
          draggable={false}
          style={{ height: SIZES[size], width: "auto", display: "block" }}
        />
      </picture>
      {label && <span className="brand-wave-label">{label}</span>}
    </span>
  );
}

export default BrandWave;