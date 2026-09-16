import { securityPillars } from "../data";
import { useScrollReveal, useStaggerReveal } from "@shared/motion";
import { LockIcon, ShieldIcon, KeyIcon, FileSearchIcon, type IconComponent } from "./Icons";

const iconMap: Record<string, IconComponent> = {
  lock: LockIcon,
  "shield-check": ShieldIcon,
  key: KeyIcon,
  "file-search": FileSearchIcon,
};

export default function Security() {
  const { ref: headerRef, motionStyle: headerStyle } = useScrollReveal();
  const { parentRef, childStyles } = useStaggerReveal({ count: securityPillars.length });

  return (
    <section className="security-section" id="security">
      <div className="section-container">
        <div className="section-header" ref={headerRef} style={headerStyle}>
          <span className="section-badge">02 — Security</span>
          <h2 className="section-title">Your data is protected by design</h2>
          <div className="section-rule" />
          <p className="section-subtitle">
            Security is not an afterthought. Every layer of the platform is built
            with privacy, encryption, and access control at its core.
          </p>
        </div>
        <div className="security-grid" ref={parentRef}>
          {securityPillars.map((pillar, i) => {
            const IconCmp = iconMap[pillar.icon] ?? ShieldIcon;
            return (
              <div key={pillar.title} className="security-card" style={childStyles[i]}>
                <div className="security-icon">
                  <IconCmp size={28} />
                </div>
                <h3 className="security-title">{pillar.title}</h3>
                <p className="security-desc">{pillar.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
