import { trustBadges } from "../data";

const iconMap: Record<string, string> = {
  bell: "🔔",
  scale: "⚖️",
  badge: "🎯",
  building: "🏢",
  shield: "🔒",
  zap: "⚡",
};

export default function TrustBadges() {
  return (
    <section className="trust-section">
      <div className="trust-grid">
        {trustBadges.map((badge) => (
          <div key={badge.title} className="trust-card">
            <div className="trust-icon">{iconMap[badge.icon]}</div>
            <div className="trust-title">{badge.title}</div>
            <div className="trust-desc">{badge.description}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
