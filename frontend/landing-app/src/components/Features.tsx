import { features } from "../data";

const iconMap: Record<string, string> = {
  receipt: "🧾",
  users: "👥",
  "layout-dashboard": "📊",
  "bell-ring": "📣",
  "file-check": "✅",
  scale: "⚖️",
};

export default function Features() {
  return (
    <section className="features-section" id="features">
      <div className="section-container">
        <div className="section-badge">Features</div>
        <h2 className="section-title">
          Everything you need to manage rent digitally
        </h2>
        <p className="section-subtitle">
          From automated rent collection to legal-ready receipts — the platform
          handles the complexity so you don't have to.
        </p>
        <div className="features-grid">
          {features.map((feature) => (
            <div key={feature.title} className="feature-card">
              <div className="feature-icon">{iconMap[feature.icon]}</div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-desc">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
