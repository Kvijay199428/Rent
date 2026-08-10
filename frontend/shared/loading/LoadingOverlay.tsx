import BrandWave from "./BrandWave";

interface LoadingOverlayProps {
  label: string;
}

export default function LoadingOverlay({ label }: LoadingOverlayProps) {
  return (
    <div className="loading-overlay" role="status">
      <BrandWave size="lg" stacked label={label} />
    </div>
  );
}
