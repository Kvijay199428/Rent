import { heroInlineBadges } from "../data";

export default function Hero() {
  return (
    <section className="hero-section" id="hero">
      <div className="hero-left">
        <div className="hero-badge">
          <span className="pulse-dot" />
          Now in Early Access — PROPAURA
        </div>

        <h1 className="hero-title">
          <span className="super-kicker">Rent Management, Engineered.</span>
          <span className="hero-title-line">Control</span>
          <span className="hero-title-line">Every</span>
          <span className="hero-title-line" style={{ color: "var(--accent)" }}>Payment.</span>
        </h1>

        <p className="hero-subtitle">
          A complete digital platform for landlords, tenants, and administrators.
          Track payments, manage properties, send receipts, and stay compliant —
          all from one place.
        </p>

        <div className="hero-inline-badges">
          {heroInlineBadges.map((badge) => (
            <span key={badge} className="inline-badge">
              {badge}
            </span>
          ))}
        </div>

        <div className="hero-actions">
          <a href="/rent/landlord/login" className="btn btn-primary">
            Landlord Login
          </a>
          <a href="#features" className="btn btn-ghost">
            Learn More
          </a>
        </div>
      </div>

      <div className="hero-right">
        <div className="hero-type-block">
          <div className="hero-type-number">01</div>
          <div className="hero-type-label">Systematic Rent Management</div>
          <div className="hero-stats">
            <div className="hero-stat">
              <div className="hero-stat-value">3</div>
              <div className="hero-stat-label">Portals</div>
            </div>
            <div className="hero-stat">
              <div className="hero-stat-value">AES</div>
              <div className="hero-stat-label">256 Bit</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
