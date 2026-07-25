export default function CTA() {
  return (
    <section className="cta-section" id="cta">
      <div className="section-container">
        <h2 className="cta-title">
          Ready to simplify rent management?
        </h2>
        <p className="cta-subtitle">
          Join the early access list and be the first to know when the platform
          launches.
        </p>
        <div className="cta-form">
          <input
            type="email"
            placeholder="Enter your email address"
            className="cta-input"
            aria-label="Email address"
          />
          <button className="btn btn-primary cta-button">Notify Me</button>
        </div>
        <p className="cta-note">
          No spam. We'll only email you when the platform is ready or when we
          have a major update.
        </p>
      </div>
    </section>
  );
}
