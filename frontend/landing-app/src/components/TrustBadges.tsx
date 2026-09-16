import { trustBadges } from "../data";
import { useStaggerReveal } from "@shared/motion";
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
  const { parentRef, childStyles } = useStaggerReveal({ count: trustBadges.length });

  return (
    <section className="trust-section">
      <div className="trust-grid" ref={parentRef}>
        {trustBadges.map((badge, i) => {
          const IconCmp = iconMap[badge.icon] ?? HomeIcon;
          return (
            <div key={badge.title} className="trust-card" style={childStyles[i]}>
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
