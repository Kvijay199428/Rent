export default function CTA() {
  return (
    <section className="cta-section" id="cta">
      <div className="section-container">
        <h2 className="cta-title">
          Ready to simplify rent management?
        </h2>
        <p className="cta-subtitle">
          The platform is live in early access. Choose your portal to get started.
        </p>
        <div className="hero-actions" style={{ justifyContent: "center" }}>
          <a href="./landlord/login" className="btn btn-primary">Landlord Login</a>
          <a href="./tenant/login" className="btn btn-outline">Tenant Login</a>
          <a href="./admin" className="btn btn-green">Admin Login</a>
        </div>
      </div>
    </section>
  );
}
