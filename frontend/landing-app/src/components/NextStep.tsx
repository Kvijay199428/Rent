const portals = [
  {
    icon: "🏠",
    title: "Landlord Portal",
    description:
      "Manage your properties, tenants, and rental receipts. New here? Create a free landlord account.",
    buttons: [
      { label: "🔑 Landlord Login", href: "./landlord/login", variant: "primary" },
      { label: "✨ Create Account", href: "./landlord/signup", variant: "secondary" },
    ],
  },
  {
    icon: "👤",
    title: "Tenant Portal",
    description:
      "Access your receipts, payment status, upload KYC documents, and manage your profile — all from a secure, encrypted portal.",
    buttons: [
      { label: "🔑 Tenant Login", href: "./tenant/login", variant: "primary" },
    ],
  },
  {
    icon: "🛡️",
    title: "Platform Admin",
    description:
      "System administration, global settings, and platform-wide oversight. Restricted access only.",
    buttons: [
      { label: "🔐 Admin Login", href: "./platform-admin", variant: "green" },
    ],
  },
];

export default function NextStep() {
  return (
    <section className="nextstep-section" id="contact">
      <div className="section-container">
        <div className="section-badge">Get Started</div>
        <h2 className="section-title">The next step</h2>
        <p className="section-subtitle">
          Choose how you'd like to access the platform.
        </p>
        <div className="nextstep-grid">
          {portals.map((portal) => (
            <div key={portal.title} className="nextstep-card">
              <div className="nextstep-icon">{portal.icon}</div>
              <h3 className="nextstep-title">{portal.title}</h3>
              <p className="nextstep-desc">{portal.description}</p>
              <div className="nextstep-buttons">
                {portal.buttons.map((btn) => (
                  <a
                    key={btn.label}
                    href={btn.href}
                    className={`btn btn-${btn.variant === "green" ? "green" : btn.variant === "secondary" ? "outline" : "primary"}`}
                  >
                    {btn.label}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
