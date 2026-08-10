import "./BrandLoading.css";

export type BrandWaveSize = "sm" | "md" | "lg";

interface BrandWaveProps {
  label?: string;
  size?: BrandWaveSize;
  stacked?: boolean;
  className?: string;
}

const BRAND = "PROPAURA";

export function BrandWave({ label, size = "md", stacked = false, className = "" }: BrandWaveProps) {
  const sizeClass =
    size === "lg" ? "loading-letters--lg" : size === "sm" ? "loading-letters--sm" : "loading-letters--md";
  return (
    <span
      className={`brand-wave ${stacked ? "brand-wave--stacked" : "brand-wave--row"} ${className}`}
      role="status"
      aria-label="PROPAURA loading"
    >
      <span className={`loading-letters ${sizeClass}`}>
        {BRAND.split("").map((ch, i) => (
          <span
            key={i}
            style={{
              color: i < 4 ? "#708498" : "#95A58F",
              animationDelay: `${i * 0.12}s`,
            }}
          >
            {ch}
          </span>
        ))}
      </span>
      {label && <span className="brand-wave-label">{label}</span>}
    </span>
  );
}

export default BrandWave;
