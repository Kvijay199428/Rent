import { securityPillars } from "../data";

const iconMap: Record<string, string> = {
  lock: "🔒",
  "shield-check": "🛡️",
  key: "🔐",
  "file-search": "📋",
};

export default function Security() {
  return (
    <section className="security-section" id="security">
      <div className="section-container">
        <div className="section-badge">Security & Privacy</div>
        <h2 className="section-title">Your data is protected by design</h2>
        <p className="section-subtitle">
          Security is not an afterthought. Every layer of the platform is built
          with privacy, encryption, and access control at its core.
        </p>
        <div className="security-grid">
          {securityPillars.map((pillar) => (
            <div key={pillar.title} className="security-card">
              <div className="security-icon">{iconMap[pillar.icon]}</div>
              <h3 className="security-title">{pillar.title}</h3>
              <p className="security-desc">{pillar.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
