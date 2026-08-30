import { ArrowUpRightIcon } from "./Icons";

export default function CTA() {
  return (
    <section className="cta-section" id="cta">
      <div className="section-container">
        <span className="cta-eyebrow">Get Started</span>
        <h2 className="cta-title">
          Ready to simplify rent management?
        </h2>
        <p className="cta-subtitle">
          The platform is live in early access. Choose your portal to get started.
        </p>
        <div className="cta-actions">
          <a href="/rent/landlord/login" className="btn btn-primary">Landlord Login</a>
          <a href="/rent/tenant/login" className="btn btn-outline">Tenant Login</a>
          <a href="/rent/admin/login" className="btn btn-ghost">Admin Login <ArrowUpRightIcon size={14} /></a>
        </div>
      </div>
    </section>
  );
}
