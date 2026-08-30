import { trustBadges } from "../data";
import { BellIcon, BuildingIcon, KeyIcon, ShieldIcon, ZapIcon, HomeIcon, type IconComponent } from "./Icons";

const iconMap: Record<string, IconComponent> = {
  bell: BellIcon,
  key: KeyIcon,
  badge: HomeIcon,
  building: BuildingIcon,
  shield: ShieldIcon,
  zap: ZapIcon,
};

export default function TrustBadges() {
  return (
    <section className="trust-section">
      <div className="trust-grid">
        {trustBadges.map((badge) => {
          const IconCmp = iconMap[badge.icon] ?? HomeIcon;
          return (
            <div key={badge.title} className="trust-card">
              <div className="trust-icon">
                <IconCmp size={24} />
              </div>
              <div className="trust-title">{badge.title}</div>
              <div className="trust-desc">{badge.description}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
