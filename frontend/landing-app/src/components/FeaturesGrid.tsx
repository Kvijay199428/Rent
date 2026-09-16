import { featureCategories } from "../data";
import { useScrollReveal, useStaggerReveal } from "@shared/motion";

export default function FeaturesGrid() {
  const { ref: headerRef, motionStyle: headerStyle } = useScrollReveal();
  const { parentRef, childStyles } = useStaggerReveal({ count: featureCategories.length });

  return (
    <section className="features-grid-section">
      <div className="section-container">
        <div className="section-header" ref={headerRef} style={headerStyle}>
          <span className="section-badge">03 — Capabilities</span>
          <h2 className="section-title">A full-stack rent management solution</h2>
          <div className="section-rule" />
          <p className="section-subtitle">
            Property management, tenant tracking, financial tools, alerts,
            documents, and admin — all unified under one roof.
          </p>
        </div>
        <div className="feature-cat-grid" ref={parentRef}>
          {featureCategories.map((cat, i) => (
            <div key={cat.title} className="feature-cat-card" style={childStyles[i]}>
              <h3 className="feature-cat-title">{cat.title}</h3>
              <ul className="feature-cat-list">
                {cat.items.map((item) => (
                  <li key={item}>
                    <span className="bullet" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
