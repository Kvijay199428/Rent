import { featureCategories } from "../data";

export default function FeaturesGrid() {
  return (
    <section className="features-grid-section">
      <div className="section-container">
        <div className="section-badge">Capabilities</div>
        <h2 className="section-title">
          A full-stack rent management solution
        </h2>
        <p className="section-subtitle">
          Property management, tenant tracking, financial tools, alerts,
          documents, and admin — all unified under one roof.
        </p>
        <div className="feature-cat-grid">
          {featureCategories.map((cat) => (
            <div key={cat.title} className="feature-cat-card">
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
