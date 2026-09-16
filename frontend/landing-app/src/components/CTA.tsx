import { useStaggerReveal } from "@shared/motion";
import { ArrowUpRightIcon } from "./Icons";

export default function CTA() {
  const { parentRef, childStyles } = useStaggerReveal({ count: 4 });

  return (
    <section className="cta-section" id="cta">
      <div className="section-container" ref={parentRef}>
        <span className="cta-eyebrow" style={childStyles[0]}>Get Started</span>
        <h2 className="cta-title" style={childStyles[1]}>
          Ready to simplify rent management?
        </h2>
        <p className="cta-subtitle" style={childStyles[2]}>
          The platform is live in early access. Choose your portal to get started.
        </p>
        <div className="cta-actions" style={childStyles[3]}>
          <a href="/landlord/login" className="btn btn-primary">Landlord Login</a>
          <a href="/tenant/login" className="btn btn-outline">Tenant Login</a>
          <a href="/admin/login" className="btn btn-ghost">Admin Login <ArrowUpRightIcon size={14} /></a>
        </div>
      </div>
    </section>
  );
}
