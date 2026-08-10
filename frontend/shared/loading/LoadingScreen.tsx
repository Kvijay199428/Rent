import { useState, useEffect } from "react";
import BrandWave from "./BrandWave";

interface LoadingScreenProps {
  isLoading: boolean;
}

export default function LoadingScreen({ isLoading }: LoadingScreenProps) {
  const [visible, setVisible] = useState(true);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    if (!isLoading && visible) {
      setFading(true);
      const timer = setTimeout(() => setVisible(false), 500);
      return () => clearTimeout(timer);
    }
  }, [isLoading, visible]);

  if (!visible) return null;

  return (
    <div className={`loading-screen ${fading ? "loading-fade-out" : ""}`}>
      <BrandWave size="lg" />
    </div>
  );
}
