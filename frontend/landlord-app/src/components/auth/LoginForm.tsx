// components/auth/LoginForm.tsx
import { useState } from "react";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { PasswordField } from "./PasswordField";
import { SocialButtons } from "./SocialButtons";
import useCapsLock from "@shared/capslock/useCapsLock";
import CapsLockWarning from "@shared/capslock/CapsLockWarning";
import type { LoginValues, SocialProvider } from "./types";

interface LoginFormProps {
  onSubmit?: (values: LoginValues) => void | Promise<void>;
  socialProviders: SocialProvider[];
  onForgot?: () => void;
}

const fieldMotion = {
  hidden: { opacity: 0, y: 8 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.05, duration: 0.25, ease: "easeOut" as const },
  }),
};

export function LoginForm({ onSubmit, socialProviders, onForgot }: LoginFormProps) {
  const capsLockOn = useCapsLock();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = identifier.trim().length > 0 && password.length > 0 && !submitting;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await onSubmit?.({ identifier: identifier.trim(), password, remember });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <CapsLockWarning isCapsLockOn={capsLockOn} />

      <motion.div custom={0} variants={fieldMotion} initial="hidden" animate="show" className="space-y-1.5">
        <Label htmlFor="login-identifier">Email, phone, or username</Label>
        <Input
          id="login-identifier"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          placeholder="you@example.com"
          autoComplete="username"
        />
      </motion.div>

      <motion.div custom={1} variants={fieldMotion} initial="hidden" animate="show">
        <PasswordField
          label="Password"
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
        />
      </motion.div>

      <motion.div
        custom={2}
        variants={fieldMotion}
        initial="hidden"
        animate="show"
        className="flex items-center justify-between text-sm"
      >
        <label className="flex items-center gap-2 text-muted-foreground">
          <Checkbox checked={remember} onCheckedChange={(v) => setRemember(v === true)} />
          Remember me
        </label>
        <button type="button" onClick={onForgot} className="text-primary hover:underline">
          Forgot password?
        </button>
      </motion.div>

      <motion.div custom={3} variants={fieldMotion} initial="hidden" animate="show">
        <Button type="submit" className="w-full" disabled={!canSubmit}>
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </motion.div>

      {socialProviders.length > 0 && (
        <motion.div custom={4} variants={fieldMotion} initial="hidden" animate="show" className="space-y-4">
          <div className="flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs uppercase tracking-wide text-muted-foreground">or</span>
            <Separator className="flex-1" />
          </div>
          <SocialButtons providers={socialProviders} actionLabel="Sign in" />
        </motion.div>
      )}
    </form>
  );
}
