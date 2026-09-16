import { useScrollReveal, useStaggerReveal } from "@shared/motion";
import { HomeIcon, UserIcon, ShieldIcon, ArrowRightIcon, type IconComponent } from "./Icons";

const portals: {
  icon: IconComponent;
  title: string;
  description: string;
  buttons: { label: string; href: string; variant: "primary" | "outline" | "green" }[];
}[] = [
  {
    icon: HomeIcon,
    title: "Landlord Portal",
    description:
      "Manage your properties, tenants, and rental receipts. New here? Create a free landlord account.",
    buttons: [
      { label: "Landlord Login", href: "/landlord/login", variant: "primary" },
      { label: "Create Account", href: "/landlord/signup", variant: "outline" },
    ],
  },
  {
    icon: UserIcon,
    title: "Tenant Portal",
    description:
      "Access your receipts, payment status, upload KYC documents, and manage your profile — all from a secure, encrypted portal.",
    buttons: [
      { label: "Tenant Login", href: "/tenant/login", variant: "primary" },
    ],
  },
  {
    icon: ShieldIcon,
    title: "Platform Admin",
    description:
      "System administration, global settings, and platform-wide oversight. Restricted access only.",
    buttons: [
      { label: "Admin Login", href: "/admin/login", variant: "green" },
    ],
  },
];

const btnClass: Record<string, string> = {
  primary: "btn-primary",
  outline: "btn-outline",
  green: "btn-primary",
};

export default function NextStep() {
  const { ref: headerRef, motionStyle: headerStyle } = useScrollReveal();
  const { parentRef, childStyles } = useStaggerReveal({ count: portals.length });

  return (
    <section className="nextstep-section" id="contact">
      <div className="section-container">
        <div className="section-header" ref={headerRef} style={headerStyle}>
          <span className="section-badge">06 — Access</span>
          <h2 className="section-title">The next step</h2>
          <div className="section-rule" />
          <p className="section-subtitle">
            Choose how you'd like to access the platform.
          </p>
        </div>
        <div className="nextstep-grid" ref={parentRef}>
          {portals.map((portal, i) => {
            const IconCmp = portal.icon;
            return (
              <div key={portal.title} className="nextstep-card" style={childStyles[i]}>
                <div className="nextstep-icon">
                  <IconCmp size={34} />
                </div>
                <h3 className="nextstep-title">{portal.title}</h3>
                <p className="nextstep-desc">{portal.description}</p>
                <div className="nextstep-buttons">
                  {portal.buttons.map((btn) => (
                    <a
                      key={btn.label}
                      href={btn.href}
                      className={`btn ${btnClass[btn.variant]}`}
                    >
                      {btn.label} <ArrowRightIcon size={14} />
                    </a>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
