import { useState, useEffect } from "react";
import Logo from "../brand/Logo";
import "./BrandLoading.css";

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
      <div className="loading-splash">
        <Logo height={64} className="loading-mark" />
      </div>
    </div>
  );
}