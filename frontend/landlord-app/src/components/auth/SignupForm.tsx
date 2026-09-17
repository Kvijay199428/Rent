// components/auth/SignupForm.tsx
import { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { Check, X, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { ROUTES } from "@/lib/routes";
import PhoneInputField from "@shared/phone/PhoneInput";
import { PasswordField } from "./PasswordField";
import { SocialButtons } from "./SocialButtons";
import { PolicyModal } from "./PolicyModal";
import { isValidEmail, isValidPhone, isValidUsername, isPasswordValid } from "@/lib/validation";
import type { SignupValues, SocialProvider } from "./types";
import type { ReactNode } from "react";

type FieldStatus = "idle" | "checking" | "available" | "taken" | "error";

interface SignupFormProps {
  onSubmit?: (values: SignupValues) => void | Promise<void>;
  socialProviders: SocialProvider[];
  termsContent?: ReactNode;
  privacyContent?: ReactNode;
}

const fieldMotion = {
  hidden: { opacity: 0, y: 8 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.05, duration: 0.25, ease: "easeOut" as const },
  }),
};

export function SignupForm({ onSubmit, socialProviders, termsContent, privacyContent }: SignupFormProps) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = useState(false);

  const [termsOpen, setTermsOpen] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);

  const [usernameStatus, setUsernameStatus] = useState<FieldStatus>("idle");
  const [emailStatus, setEmailStatus] = useState<FieldStatus>("idle");
  const [usernameSuggestions, setUsernameSuggestions] = useState<string[]>([]);

  const usernameTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const emailTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const fullNameValid = fullName.trim().length >= 2;
  const emailValid = isValidEmail(email);
  const phoneValid = phone.trim().length === 0 || isValidPhone(phone);
  const usernameValid = isValidUsername(username);
  const passwordValid = isPasswordValid(password);
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  const hasFilledFields =
    fullName.trim().length > 0 &&
    email.trim().length > 0 &&
    username.trim().length > 0 &&
    password.length > 0 &&
    confirmPassword.length > 0;

  const policiesAccepted = acceptedTerms && acceptedPrivacy && hasFilledFields;
  const allFieldsValid =
    fullNameValid && emailValid && phoneValid && usernameValid && passwordValid && passwordsMatch;
  const canSubmit = allFieldsValid && policiesAccepted && !submitting;

  const checkUsername = useCallback((value: string) => {
    if (usernameTimer.current) clearTimeout(usernameTimer.current);
    if (value.length < 3) {
      setUsernameStatus("idle");
      setUsernameSuggestions([]);
      return;
    }
    setUsernameStatus("checking");
    usernameTimer.current = setTimeout(async () => {
      try {
        const res = await fetch(`${ROUTES.LANDLORDAPIAUTHCHECKUSERNAME}?username=${encodeURIComponent(value)}`);
        const data = await res.json();
        if (data.available) {
          setUsernameStatus("available");
          setUsernameSuggestions([]);
        } else {
          setUsernameStatus("taken");
          setUsernameSuggestions(data.suggestions || []);
        }
      } catch {
        setUsernameStatus("error");
      }
    }, 400);
  }, []);

  const checkEmail = useCallback((value: string) => {
    if (emailTimer.current) clearTimeout(emailTimer.current);
    if (!value.includes("@") || value.length < 5) {
      setEmailStatus("idle");
      return;
    }
    setEmailStatus("checking");
    emailTimer.current = setTimeout(async () => {
      try {
        const res = await fetch(`${ROUTES.LANDLORDAPIAUTHCHECKEMAIL}?email=${encodeURIComponent(value)}`);
        const data = await res.json();
        setEmailStatus(data.available ? "available" : "taken");
        if (!data.available) {
          toast.error("Email is already registered", { description: "Please use a different email or log in." });
        }
      } catch {
        setEmailStatus("error");
      }
    }, 500);
  }, []);

  function handleField(field: string, value: string) {
    setTouched((t) => ({ ...t, [field]: true }));

    if (field === "fullName") {
      setFullName(value);
    } else if (field === "email") {
      setEmail(value);
      checkEmail(value);
    } else if (field === "username") {
      const clean = value.toLowerCase().replace(/[^a-z0-9_]/g, "");
      setUsername(clean !== value ? clean : value);
      checkUsername(clean);
    } else if (field === "phone") {
      setPhone(value);
    } else if (field === "password") {
      setPassword(value);
    }
  }

  const selectSuggestion = (s: string) => {
    setUsername(s);
    setUsernameStatus("available");
    setUsernameSuggestions([]);
    toast.success(`Username "${s}" is available`);
  };

  function markTouched(field: string) {
    setTouched((t) => ({ ...t, [field]: true }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await onSubmit?.({
        fullName: fullName.trim(),
        email: email.trim(),
        phone: phone.trim(),
        username: username.trim(),
        password,
      });
    } finally {
      setSubmitting(false);
    }
  }

  const fieldIcon = (status: FieldStatus) => {
    if (status === "checking") return <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />;
    if (status === "available") return <Check className="h-4 w-4 text-green-500" />;
    if (status === "taken" || status === "error") return <X className="h-4 w-4 text-red-500" />;
    return null;
  };

  const fieldBorder = (status: FieldStatus) => {
    if (status === "available") return "border-green-500 focus-visible:ring-green-500";
    if (status === "taken" || status === "error") return "border-red-500 focus-visible:ring-red-500";
    return "";
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="space-y-4">
        <motion.div custom={0} variants={fieldMotion} initial="hidden" animate="show" className="space-y-1.5">
          <Label htmlFor="signup-fullname">Full name</Label>
          <Input
            id="signup-fullname"
            value={fullName}
            onChange={(e) => handleField("fullName", e.target.value)}
            onBlur={() => markTouched("fullName")}
            placeholder="Jane Doe"
            autoComplete="name"
            className={cn(touched.fullName && !fullNameValid && fullName.length > 0 && "border-destructive")}
          />
          {touched.fullName && fullName.length > 0 && !fullNameValid && (
            <p className="text-xs text-destructive">Enter your full name (at least 2 characters).</p>
          )}
        </motion.div>

        <motion.div custom={1} variants={fieldMotion} initial="hidden" animate="show" className="space-y-1.5">
          <Label htmlFor="signup-email">Email address</Label>
          <div className="relative">
            <Input
              id="signup-email"
              type="email"
              value={email}
              onChange={(e) => handleField("email", e.target.value)}
              onBlur={() => markTouched("email")}
              placeholder="you@example.com"
              autoComplete="email"
              className={cn(
                fieldBorder(emailStatus),
                touched.email && !emailValid && email.length > 0 && "border-destructive",
                emailStatus !== "idle" && "pr-9"
              )}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2">{fieldIcon(emailStatus)}</span>
          </div>
          {emailStatus === "taken" && (
            <p className="text-xs text-red-500">This email is already registered.</p>
          )}
          {touched.email && email.length > 0 && !emailValid && emailStatus !== "taken" && (
            <p className="text-xs text-destructive">Enter a valid email address.</p>
          )}
        </motion.div>

        <motion.div custom={2} variants={fieldMotion} initial="hidden" animate="show" className="space-y-1.5">
          <Label htmlFor="signup-username">Choose a username</Label>
          <div className="relative">
            <Input
              id="signup-username"
              value={username}
              onChange={(e) => handleField("username", e.target.value)}
              onBlur={() => markTouched("username")}
              placeholder="janedoe"
              autoComplete="off"
              className={cn(
                fieldBorder(usernameStatus),
                touched.username && !usernameValid && username.length > 0 && "border-destructive",
                usernameStatus !== "idle" && "pr-9"
              )}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2">{fieldIcon(usernameStatus)}</span>
          </div>
          {usernameSuggestions.length > 0 && (
            <div className="p-3 bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800 rounded-md">
              <p className="text-sm text-orange-700 dark:text-orange-300 font-medium mb-2">
                "{username}" is taken. Try one of these:
              </p>
              <div className="flex flex-wrap gap-2">
                {usernameSuggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => selectSuggestion(s)}
                    className="px-3 py-1 bg-white dark:bg-orange-900 border border-orange-300 dark:border-orange-700 rounded-full text-sm text-orange-700 dark:text-orange-200 hover:bg-orange-100 dark:hover:bg-orange-800 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            {touched.username && username.length > 0 && !usernameValid
              ? "3-20 characters, start with a letter, letters/numbers/underscore only."
              : "You can sign in later with this username instead of your email."}
          </p>
        </motion.div>

        <motion.div custom={3} variants={fieldMotion} initial="hidden" animate="show" className="space-y-1.5">
          <Label htmlFor="signup-phone">Phone (optional)</Label>
          <PhoneInputField
            id="signup-phone"
            placeholder="Mobile number"
            value={phone}
            onChange={(value) => handleField("phone", value || "")}
          />
          {touched.phone && phone.length > 0 && !isValidPhone(phone) && (
            <p className="text-xs text-destructive">Enter a valid phone number, digits only.</p>
          )}
        </motion.div>

        <motion.div custom={4} variants={fieldMotion} initial="hidden" animate="show">
          <PasswordField
            label="Password"
            value={password}
            onChange={setPassword}
            showRules
            highlightValid={passwordsMatch && passwordValid}
          />
        </motion.div>

        <motion.div custom={5} variants={fieldMotion} initial="hidden" animate="show">
          <PasswordField
            label="Re-enter password"
            value={confirmPassword}
            onChange={setConfirmPassword}
            compareTo={password}
          />
        </motion.div>

        <motion.div custom={6} variants={fieldMotion} initial="hidden" animate="show" className="space-y-2 pt-1">
          <label
            className={cn(
              "flex items-start gap-2 text-sm transition-opacity",
              hasFilledFields ? "text-muted-foreground" : "text-muted-foreground/50"
            )}
          >
            <Checkbox
              checked={acceptedTerms && hasFilledFields}
              onCheckedChange={(v) => setAcceptedTerms(v === true)}
              disabled={!hasFilledFields}
              className="mt-0.5"
            />
            <span>
              I agree to the{" "}
              <button
                type="button"
                onClick={() => setTermsOpen(true)}
                disabled={!hasFilledFields}
                className="text-primary underline-offset-2 hover:underline disabled:pointer-events-none disabled:no-underline disabled:text-muted-foreground/50"
              >
                Terms and Conditions
              </button>
            </span>
          </label>
          <label
            className={cn(
              "flex items-start gap-2 text-sm transition-opacity",
              hasFilledFields ? "text-muted-foreground" : "text-muted-foreground/50"
            )}
          >
            <Checkbox
              checked={acceptedPrivacy && hasFilledFields}
              onCheckedChange={(v) => setAcceptedPrivacy(v === true)}
              disabled={!hasFilledFields}
              className="mt-0.5"
            />
            <span>
              I agree to the{" "}
              <button
                type="button"
                onClick={() => setPrivacyOpen(true)}
                disabled={!hasFilledFields}
                className="text-primary underline-offset-2 hover:underline disabled:pointer-events-none disabled:no-underline disabled:text-muted-foreground/50"
              >
                Privacy Policy
              </button>
            </span>
          </label>
          {!hasFilledFields && (
            <p className="text-xs text-muted-foreground">
              Fill in the fields above to unlock these checkboxes.
            </p>
          )}
        </motion.div>

        <motion.div custom={7} variants={fieldMotion} initial="hidden" animate="show">
          <Button type="submit" className="w-full" disabled={!canSubmit}>
            {submitting ? "Creating account…" : "Create account"}
          </Button>
        </motion.div>

        {socialProviders.length > 0 && (
          <motion.div custom={8} variants={fieldMotion} initial="hidden" animate="show" className="space-y-4">
            <div className="flex items-center gap-3">
              <Separator className="flex-1" />
              <span className="text-xs uppercase tracking-wide text-muted-foreground">or</span>
              <Separator className="flex-1" />
            </div>
            <SocialButtons providers={socialProviders} disabled={!policiesAccepted} actionLabel="Sign up" />
            {!policiesAccepted && (
              <p className="text-center text-xs text-muted-foreground">
                {hasFilledFields
                  ? "Accept the Terms and Privacy Policy to continue."
                  : "Fill in the fields above, then accept the Terms and Privacy Policy to continue."}
              </p>
            )}
          </motion.div>
        )}
      </form>

      <PolicyModal
        open={termsOpen}
        onOpenChange={setTermsOpen}
        title="Terms and Conditions"
        content={termsContent}
      />
      <PolicyModal
        open={privacyOpen}
        onOpenChange={setPrivacyOpen}
        title="Privacy Policy"
        content={privacyContent}
      />
    </>
  );
}