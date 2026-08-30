import { features } from "../data";
import { ReceiptIcon, TeamIcon, HomeIcon, BellIcon, DatabaseIcon, SpreadsheetIcon, type IconComponent } from "./Icons";

const iconMap: Record<string, IconComponent> = {
  receipt: ReceiptIcon,
  users: TeamIcon,
  home: HomeIcon,
  "bell-ring": BellIcon,
  database: DatabaseIcon,
  "file-spreadsheet": SpreadsheetIcon,
};

export default function Features() {
  return (
    <section className="features-section" id="features">
      <div className="section-container">
        <div className="section-header">
          <span className="section-badge">01 — Features</span>
          <h2 className="section-title">
            Everything you need to manage rent digitally
          </h2>
          <div className="section-rule" />
          <p className="section-subtitle">
            From digital receipts to encrypted tenant login — the platform
            handles the complexity so you don't have to.
          </p>
        </div>
        <div className="features-grid">
          {features.map((feature, i) => {
            const IconCmp = iconMap[feature.icon] ?? HomeIcon;
            return (
              <div key={feature.title} className="feature-card">
                <span className="feature-index">{String(i + 1).padStart(2, "0")}</span>
                <div className="feature-icon">
                  <IconCmp size={30} />
                </div>
                <h3 className="feature-title">{feature.title}</h3>
                <p className="feature-desc">{feature.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
