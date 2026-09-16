import { heroInlineBadges } from "../data";
import { Logo } from "@shared/brand/Logo";

const revealStyle = (delay: number) =>
  delay > 0 ? { animationDelay: `${delay}s` } : undefined;

export default function Hero() {
  return (
    <section className="hero-section" id="hero">
      <div className="hero-left">
        <div className="hero-badge motion-fade-up" style={revealStyle(0.05)}>
          <span className="pulse-dot" />
          Now in Early Access — <Logo height={14} />
        </div>

        <h1 className="hero-title">
          <span className="super-kicker motion-fade-up" style={revealStyle(0.1)}>Rent Management, Engineered.</span>
          <span className="hero-title-line motion-fade-up" style={revealStyle(0.16)}>Control</span>
          <span className="hero-title-line motion-fade-up" style={revealStyle(0.22)}>Every</span>
          <span className="hero-title-line motion-fade-up" style={{ color: "var(--accent)", animationDelay: "0.28s" }}>Payment.</span>
        </h1>

        <p className="hero-subtitle motion-fade-up" style={revealStyle(0.34)}>
          A complete digital platform for landlords, tenants, and administrators.
          Track payments, manage properties, send receipts, and stay compliant —
          all from one place.
        </p>

        <div className="hero-inline-badges motion-fade-up" style={revealStyle(0.4)}>
          {heroInlineBadges.map((badge) => (
            <span key={badge} className="inline-badge">
              {badge}
            </span>
          ))}
        </div>

        <div className="hero-actions motion-fade-up" style={revealStyle(0.46)}>
          <a href="/landlord/login" className="btn btn-primary">
            Landlord Login
          </a>
          <a href="#features" className="btn btn-ghost">
            Learn More
          </a>
        </div>
      </div>

      <div className="hero-right motion-fade-up" style={revealStyle(0.5)}>
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