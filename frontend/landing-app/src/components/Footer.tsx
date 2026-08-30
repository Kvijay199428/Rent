export default function Footer() {
  const year = new Date().getFullYear();

  const sitemap: { heading: string; links: { label: string; href: string }[] }[] = [
    {
      heading: "Platform",
      links: [
        { label: "Features", href: "#features" },
        { label: "Benefits", href: "#benefits" },
        { label: "Security", href: "#security" },
        { label: "Roadmap", href: "#roadmap" },
        { label: "FAQ", href: "#faq" },
      ],
    },
    {
      heading: "Logins",
      links: [
        { label: "Landlord Login", href: "/rent/landlord/login" },
        { label: "Create Landlord Account", href: "/rent/landlord/signup" },
        { label: "Tenant Login", href: "/rent/tenant/login" },
        { label: "Admin Login", href: "/rent/admin/login" },
      ],
    },
    {
      heading: "Resources",
      links: [
        { label: "Help Center", href: "#contact" },
        { label: "System Status", href: "#contact" },
        { label: "Report a Bug", href: "#contact" },
        { label: "Contact Us", href: "mailto:vijaykrsha@hotmail.com" },
      ],
    },
    {
      heading: "Legal",
      links: [
        { label: "Privacy Policy", href: "/rent/landlord/privacy-policy" },
        { label: "Terms of Service", href: "/rent/landlord/terms" },
      ],
    },
  ];

  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <div className="footer-logo">
            <span className="logo-icon" style={{ width: 38, height: 38, fontSize: 15 }}>PA</span>
            <span className="logo-text">
              <span style={{ color: "#fff" }}>PROP</span>
              <span style={{ color: "var(--accent)" }}>AURA</span>
            </span>
          </div>
          <p className="footer-tagline">
            A complete digital platform for landlords, tenants, and administrators.
            Sitemap. All rights reserved.
          </p>
        </div>

        {sitemap.map((col) => (
          <div key={col.heading} className="footer-col">
            <h4 className="footer-heading">{col.heading}</h4>
            <ul>
              {col.links.map((link) => (
                <li key={link.label}>
                  <a href={link.href}>{link.label}</a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="footer-bottom">
        <p>&copy; {year} PROPAURA by Vijay Kumar Sharma. All rights reserved.</p>
        <div className="footer-bottom-links">
          <a href="/rent/landlord/privacy-policy">Privacy Policy</a>
          <a href="/rent/landlord/terms">Terms of Service</a>
        </div>
      </div>
    </footer>
  );
}
