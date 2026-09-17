// components/auth/SocialButtons.tsx
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import type { SocialProvider } from "./types";

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.52 12.27c0-.85-.08-1.67-.22-2.45H12v4.64h6.48a5.54 5.54 0 0 1-2.4 3.64v3h3.88c2.27-2.09 3.56-5.17 3.56-8.83z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.07 7.93-2.9l-3.88-3c-1.08.72-2.45 1.15-4.05 1.15-3.12 0-5.76-2.1-6.7-4.93H1.3v3.1A12 12 0 0 0 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.3 14.32a7.2 7.2 0 0 1 0-4.64v-3.1H1.3a12 12 0 0 0 0 10.84z"
      />
      <path
        fill="#EA4335"
        d="M12 4.77c1.76 0 3.34.6 4.58 1.79l3.44-3.44C17.94 1.19 15.24 0 12 0A12 12 0 0 0 1.3 6.58l4 3.1C6.24 6.86 8.88 4.77 12 4.77z"
      />
    </svg>
  );
}

interface SocialButtonsProps {
  providers: SocialProvider[];
  disabled?: boolean;
  actionLabel: "Sign in" | "Sign up";
}

export function SocialButtons({ providers, disabled, actionLabel }: SocialButtonsProps) {
  if (!providers.length) return null;

  return (
    <div className={`grid gap-2 ${providers.length > 1 ? "sm:grid-cols-2" : ""}`}>
      {providers.map((provider) => (
        <motion.div key={provider.id} whileTap={{ scale: disabled || provider.disabled ? 1 : 0.98 }}>
          <Button
            type="button"
            variant="outline"
            className="w-full gap-2"
            disabled={disabled || provider.disabled}
            onClick={provider.onClick}
          >
            {provider.icon ?? (provider.id === "google" ? <GoogleIcon /> : null)}
            {actionLabel} with {provider.label}
          </Button>
        </motion.div>
      ))}
    </div>
  );
}
