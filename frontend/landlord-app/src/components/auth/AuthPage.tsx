// components/auth/AuthPage.tsx
import { motion } from "framer-motion";
import { AuthFlow } from "./AuthFlow";
import { BrandLogo } from "./BrandLogo";
import type { AuthFlowProps } from "./types";

interface AuthPageProps extends AuthFlowProps {
  /** Headline shown on the decorative side panel (desktop only). */
  heroTitle?: string;
  heroDescription?: string;
}

/**
 * Full-page auth screen: a quiet brand panel on the left (desktop),
 * the AuthFlow card on the right. Collapses to a single column on mobile.
 * Use this as the default export for a route like /login.
 */
export function AuthPage({
  heroTitle = "Welcome back",
  heroDescription = "Sign in to pick up right where you left off.",
  ...authFlowProps
}: AuthPageProps) {
  return (
    <div className="min-h-screen w-full bg-background lg:grid lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-foreground text-background lg:flex lg:flex-col lg:justify-between lg:p-12">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        >
          <BrandLogo logo={authFlowProps.logo} brandName={authFlowProps.brandName} size={32} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
          className="max-w-sm space-y-3"
        >
          <h1 className="text-3xl font-semibold leading-tight">{heroTitle}</h1>
          <p className="text-background/70">{heroDescription}</p>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-xs text-background/50"
        >
          © {new Date().getFullYear()} {authFlowProps.brandName ?? "Your Product"}. All rights reserved.
        </motion.p>
      </div>

      <div className="flex min-h-screen items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
        >
          <AuthFlow {...authFlowProps} />
        </motion.div>
      </div>
    </div>
  );
}
