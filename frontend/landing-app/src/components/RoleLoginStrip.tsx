import { ArrowRightIcon, HomeIcon, ShieldIcon, UserIcon } from "./Icons";

const roles = [
  {
    icon: HomeIcon,
    eyebrow: "Property Owner",
    title: "Landlord",
    desc: "Manage tenants, billing & receipts",
    href: "/rent/landlord/login",
  },
  {
    icon: UserIcon,
    eyebrow: "Self Service",
    title: "Tenant",
    desc: "View receipts, pay status & KYC",
    href: "/rent/tenant/login",
  },
  {
    icon: ShieldIcon,
    eyebrow: "Restricted",
    title: "Admin",
    desc: "Platform oversight & settings",
    href: "/rent/admin/login",
  },
];

export default function RoleLoginStrip() {
  return (
    <section className="role-strip" aria-label="Portal logins">
      <div className="role-strip-inner">
        {roles.map((role) => {
          const IconCmp = role.icon;
          return (
            <a key={role.title} href={role.href} className="role-card">
              <span className="role-icon">
                <IconCmp size={26} />
              </span>
              <span className="role-body">
                <span className="role-eyebrow">{role.eyebrow}</span>
                <span className="role-title">{role.title} Login</span>
                <span className="role-desc">{role.desc}</span>
              </span>
              <span className="role-arrow" aria-hidden="true">
                <ArrowRightIcon size={22} />
              </span>
            </a>
          );
        })}
      </div>
    </section>
  );
}
