// components/auth/AuthFlow.tsx
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import {
  Alert,
  AlertDescription,
} from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { BrandLogo } from "./BrandLogo";
import { LoginForm } from "./LoginForm";
import { SignupForm } from "./SignupForm";
import type { AuthFlowProps } from "./types";

type Tab = "login" | "signup";

/**
 * Self-contained login + signup flow: animated tab switch, social login,
 * live password validation, and built-in Terms/Privacy modals.
 * Drop it anywhere — it only needs the shadcn/ui primitives listed in the README.
 */
export function AuthFlow({
  logo,
  brandName = "Your Product",
  tagline,
  socialProviders = [],
  onLogin,
  onSignup,
  onForgotPassword,
  termsContent,
  privacyContent,
  error,
  onTabChange,
  defaultTab = "login",
  className,
}: AuthFlowProps) {
  const [tab, setTab] = useState<Tab>(defaultTab);

  function switchTab(next: Tab) {
    setTab(next);
    onTabChange?.(next);
  }

  return (
    <Card className={cn("w-full max-w-md overflow-hidden", className)}>
      <CardHeader className="space-y-4 pb-2">
        <div className="flex items-center gap-3">
          <BrandLogo logo={logo} brandName={brandName} />
          <div>
            <p className="font-medium leading-none">{brandName}</p>
            {tagline && <p className="text-sm text-muted-foreground mt-1">{tagline}</p>}
          </div>
        </div>

        <div className="relative grid grid-cols-2 rounded-lg bg-muted p-1 text-sm font-medium">
          {(["login", "signup"] as Tab[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => switchTab(t)}
              className={cn(
                "relative z-10 rounded-md py-1.5 transition-colors",
                tab === t ? "text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              {t === "login" ? "Sign in" : "Sign up"}
            </button>
          ))}
          <motion.div
            className="absolute inset-y-1 w-[calc(50%-4px)] rounded-md bg-background shadow-sm"
            animate={{ x: tab === "login" ? 4 : "calc(100% + 4px)" }}
            transition={{ type: "spring", stiffness: 400, damping: 32 }}
          />
        </div>
      </CardHeader>

      <CardContent className="pt-4 overflow-hidden">
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={tab}
            initial={{ opacity: 0, x: tab === "login" ? -16 : 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: tab === "login" ? 16 : -16 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            {tab === "login" ? (
              <LoginForm onSubmit={onLogin} socialProviders={socialProviders} onForgot={onForgotPassword} />
            ) : (
              <SignupForm
                onSubmit={onSignup}
                socialProviders={socialProviders}
                termsContent={termsContent}
                privacyContent={privacyContent}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </CardContent>

      <CardFooter className="justify-center pb-6 pt-0">
        <button
          type="button"
          onClick={() => switchTab(tab === "login" ? "signup" : "login")}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {tab === "login" ? "Don't have an account? " : "Already have an account? "}
          <span className="font-medium text-primary">{tab === "login" ? "Sign up" : "Sign in"}</span>
        </button>
      </CardFooter>
    </Card>
  );
}
