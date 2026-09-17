// components/auth/PasswordField.tsx
import { useState, useId } from "react";
import { Eye, EyeOff, Check, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { checkPasswordRules, getPasswordStrength, isPasswordValid } from "@/lib/validation";

interface PasswordFieldProps {
  id?: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  autoComplete?: string;
  /** Primary password field: shows the live rule checklist + strength meter. */
  showRules?: boolean;
  /** Primary password field: turn the outline green once a valid confirm-match exists. */
  highlightValid?: boolean;
  /** Confirm field: pass the primary password value to compare against. Presence of this prop = "confirm mode". */
  compareTo?: string;
}

const strengthMeta: Record<string, { width: string; className: string }> = {
  empty: { width: "0%", className: "bg-transparent" },
  weak: { width: "33%", className: "bg-destructive" },
  medium: { width: "66%", className: "bg-amber-500" },
  strong: { width: "100%", className: "bg-emerald-500" },
};

export function PasswordField({
  id,
  label,
  value,
  onChange,
  placeholder = "••••••••",
  autoComplete = "new-password",
  showRules = false,
  highlightValid = false,
  compareTo,
}: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const isConfirmField = compareTo !== undefined;

  const rules = checkPasswordRules(value);
  const strength = getPasswordStrength(value);

  const matches = isConfirmField && value.length > 0 && value === compareTo;
  const confirmValid = isConfirmField && matches && isPasswordValid(compareTo ?? "");
  const showGreenRing = isConfirmField ? confirmValid : highlightValid;

  return (
    <div className="space-y-1.5">
      <Label htmlFor={fieldId}>{label}</Label>
      <div className="relative">
        <Input
          id={fieldId}
          type={visible ? "text" : "password"}
          value={value}
          placeholder={placeholder}
          autoComplete={autoComplete}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "pr-20 transition-colors duration-200",
            showGreenRing && "border-emerald-500 ring-2 ring-emerald-500/30 focus-visible:ring-emerald-500/40"
          )}
        />
        <div className="absolute inset-y-0 right-2 flex items-center gap-1.5">
          <AnimatePresence>
            {isConfirmField && value.length > 0 && (
              <motion.span
                initial={{ opacity: 0, scale: 0.6 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.6 }}
                transition={{ type: "spring", stiffness: 400, damping: 20 }}
              >
                {matches ? (
                  <Check className="h-4 w-4 text-emerald-500" />
                ) : (
                  <X className="h-4 w-4 text-destructive" />
                )}
              </motion.span>
            )}
          </AnimatePresence>
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            className="text-muted-foreground hover:text-foreground transition-colors"
            aria-label={visible ? "Hide password" : "Show password"}
            tabIndex={-1}
          >
            {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {showRules && (
        <div className="space-y-2 pt-1">
          <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
            <motion.div
              className={cn("h-full rounded-full", strengthMeta[strength].className)}
              initial={false}
              animate={{ width: strengthMeta[strength].width }}
              transition={{ type: "spring", stiffness: 260, damping: 30 }}
            />
          </div>
          <ul className="grid grid-cols-2 gap-x-3 gap-y-1">
            {rules.map((rule) => (
              <li
                key={rule.id}
                className={cn(
                  "flex items-center gap-1 text-xs transition-colors",
                  rule.passed ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground"
                )}
              >
                {rule.passed ? (
                  <Check className="h-3 w-3 shrink-0" />
                ) : (
                  <X className="h-3 w-3 shrink-0 opacity-50" />
                )}
                {rule.label}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
