export const navLinks = [
  { label: "Features", href: "#features" },
  { label: "Benefits", href: "#benefits" },
  { label: "Security", href: "#security" },
  { label: "FAQ", href: "#faq" },
  { label: "Contact Us", href: "#contact" },
];

export const trustBadges = [
  {
    icon: "bell",
    title: "Smart Alerts",
    description: "WhatsApp notifications for rent receipts and payment reminders.",
  },
  {
    icon: "key",
    title: "Encrypted Login",
    description: "RSA+AES-256-GCM encrypted PIN authentication for tenant portal access.",
  },
  {
    icon: "badge",
    title: "Free Core",
    description: "Core rent management features are free forever for all landlords.",
  },
  {
    icon: "building",
    title: "Multi-Property",
    description: "Manage multiple landlords, tenants, and billing from one dashboard.",
  },
  {
    icon: "shield",
    title: "Private & Secure",
    description: "Role-based access, encrypted cookies, and audit logging built in.",
  },
  {
    icon: "zap",
    title: "Fast Setup",
    description: "Add your first tenant in under 2 minutes. No training required.",
  },
];

export const heroInlineBadges = [
  "Encrypted Login",
  "PDF Receipts",
  "WhatsApp Alerts",
];

export const features = [
  {
    icon: "receipt",
    title: "Digital Receipts",
    description:
      "Generate professional PDF receipts for every payment. Track paid, partial, pending, and advance statuses.",
  },
  {
    icon: "users",
    title: "Tenant Management",
    description:
      "Complete tenant profiles with encrypted PIN access, room assignments, and KYC document uploads.",
  },
  {
    icon: "home",
    title: "Tenant Self-Service Portal",
    description:
      "Tenants access their own portal via username + encrypted PIN to view receipts, upload KYC, and check payment status.",
  },
  {
    icon: "bell-ring",
    title: "WhatsApp Notifications",
    description:
      "Send rent receipts and payment reminders directly via WhatsApp with a single click.",
  },
  {
    icon: "database",
    title: "Backup & Restore",
    description:
      "Manual backups with integrity verification, one-click restore, and downloadable backup files.",
  },
  {
    icon: "file-spreadsheet",
    title: "Data Import & Export",
    description:
      "Import tenant and billing data via CSV or Excel. Export receipts, tenant data, and full archives with real-time progress.",
  },
];

export const whyChooseFeatures = [
  "Track every payment in real-time — paid, partial, pending, or advance",
  "Send WhatsApp receipts and reminders with one click",
  "Professional PDF receipts, instantly downloadable",
  "Works on any device — phone, tablet, or desktop",
  "Encrypted tenant login with RSA + AES-256-GCM security",
  "Free for landlords — full billing and tenant management",
];

export const screenshotTabs = ["Dashboard", "Tenants", "Payments"];

export const featureCategories = [
  {
    title: "Billing & Receipts",
    items: [
      "Generate monthly bills with one click",
      "Track payment status: paid, partial, pending, advance",
      "Download professional PDF receipts",
      "Archive old bills with occupant context",
    ],
  },
  {
    title: "Tenant Management",
    items: [
      "Complete tenant profiles with room assignments",
      "Encrypted PIN-based and username+PIN login",
      "KYC document uploads (Aadhaar, employment)",
      "Account lockout after failed login attempts",
    ],
  },
  {
    title: "Payment Tracking",
    items: [
      "Real-time payment status across all tenants",
      "Arrears and advance payment tracking",
      "Security deposit records",
      "Complete receipt history with search",
    ],
  },
  {
    title: "Security & Privacy",
    items: [
      "RSA-OAEP + AES-256-GCM encrypted login",
      "Role-based access (Admin, Landlord, Tenant)",
      "Secure httponly cookies with path scoping",
      "Audit logging for all actions",
    ],
  },
  {
    title: "Data Management",
    items: [
      "Manual backups with integrity verification",
      "CSV and Excel import/export",
      "Real-time sync progress via WebSocket",
      "One-click data restore from backup",
    ],
  },
  {
    title: "Platform Administration",
    items: [
      "Multi-landlord oversight dashboard",
      "Global platform settings",
      "System health monitoring",
      "Broadcast messaging to all users",
    ],
  },
];

export const securityPillars = [
  {
    icon: "lock",
    title: "Encrypted Authentication",
    description:
      "Tenant PIN login uses RSA-OAEP key exchange and AES-256-GCM encryption. Credentials never travel in plaintext.",
  },
  {
    icon: "shield-check",
    title: "Role-Based Access",
    description:
      "Three distinct roles (Platform Admin, Landlord, Tenant) with strict data isolation. Each role sees only what they're authorized to access.",
  },
  {
    icon: "key",
    title: "Brute-Force Protection",
    description:
      "Tenant accounts lock after 5 failed PIN attempts for 15 minutes. Failed attempts are logged with IP tracking.",
  },
  {
    icon: "file-search",
    title: "Audit Logging",
    description:
      "Every login, failed attempt, and administrative action is logged with timestamps and IP addresses for full accountability.",
  },
];

export const roadmapMilestones = [
  {
    version: "v1.0",
    title: "Core Platform",
    description:
      "Tenant management, billing, digital receipts, dashboard, and multi-landlord support.",
    status: "completed" as const,
  },
  {
    version: "v1.5",
    title: "Advanced Features",
    description:
      "KYC uploads, data backup & restore, CSV/Excel import/export, and tenant self-service portal.",
    status: "completed" as const,
  },
  {
    version: "v2.0",
    title: "Tenant Self-Service",
    description:
      "Username + PIN login, tenant profile details, cross-app navigation, and broadcast messaging.",
    status: "in-progress" as const,
  },
  {
    version: "v3.0",
    title: "Analytics & API",
    description:
      "Revenue analytics, occupancy trends, public API, and accounting integrations.",
    status: "upcoming" as const,
  },
];

export const faqItems = [
  {
    question: "Is the platform free for landlords?",
    answer:
      "Yes. Core features — adding tenants, generating bills, creating receipts, and sending WhatsApp notifications — are free for all landlords.",
  },
  {
    question: "How do tenants access their portal?",
    answer:
      "Tenants receive a secure link from their landlord. They can log in using their phone/email + 4-digit PIN. The portal shows their receipts, payment status, and allows KYC document uploads.",
  },
  {
    question: "How does WhatsApp integration work?",
    answer:
      "Landlords can send rent receipts and payment reminders directly to tenants via WhatsApp. Messages are sent with one click from the billing page.",
  },
  {
    question: "Is my data secure?",
    answer:
      "Yes. Tenant PIN login uses RSA + AES-256-GCM encryption. Cookies are httponly and secure. Each landlord's data is fully isolated. Accounts lock after 5 failed login attempts.",
  },
  {
    question: "Can I import existing data?",
    answer:
      "Yes. The platform supports importing tenants and billing data via CSV or Excel. A preview step lets you verify data before importing. Full data export is also available.",
  },
];

export const supportLinks = [
  "Help Center",
  "System Status",
  "Report a Bug",
];
