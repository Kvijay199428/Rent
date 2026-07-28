import { heroInlineBadges } from "../data";

export default function Hero() {
  return (
    <section className="hero-section" id="hero">
      <div className="hero-animated-logo" aria-hidden="true">
        <div className="animated-logo-placeholder">
          <span>P</span>
        </div>
      </div>

      <div className="hero-badge">
        <span className="pulse-dot" />
        Now in Early Access — PROPAURA
      </div>

      <h1 className="hero-title">
        <span style={{color:"#708498"}}>PROP</span>
        <br />
        <span className="gradient-text"><span style={{color:"#95A58F"}}>AURA</span></span>
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
        <a href="#contact" className="btn btn-primary">
          Get Started
        </a>
        <a href="#features" className="btn btn-ghost">
          Learn More
        </a>
      </div>
    </section>
  );
}
