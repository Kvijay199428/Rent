import { useState, useEffect } from "react";
import "./LoadingScreen.css";

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
      <div className="loading-brand">
        <span className="loading-prop">PROP</span>
        <span className="loading-aura">AURA</span>
      </div>
      <div className="loading-spinner" />
    </div>
  );
}
