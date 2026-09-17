// lib/validation.ts
// Framework-agnostic validation used by LoginForm and SignupForm.
// No external deps — safe to copy into any project.

export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Accepts +countrycode and 7-15 digits, spaces/dashes stripped before testing.
export const PHONE_REGEX = /^\+?[0-9]{7,15}$/;

// 3-20 chars, must start with a letter, letters/numbers/underscore only.
export const USERNAME_REGEX = /^[A-Za-z][A-Za-z0-9_]{2,19}$/;

export interface PasswordRuleResult {
  id: string;
  label: string;
  passed: boolean;
}

/**
 * Industry-standard baseline: 8+ chars, upper, lower, number, special char.
 * Returns each rule's pass/fail so the UI can render a live checklist.
 */
export function checkPasswordRules(password: string): PasswordRuleResult[] {
  return [
    { id: "length", label: "At least 8 characters", passed: password.length >= 8 },
    { id: "upper", label: "One uppercase letter", passed: /[A-Z]/.test(password) },
    { id: "lower", label: "One lowercase letter", passed: /[a-z]/.test(password) },
    { id: "number", label: "One number", passed: /[0-9]/.test(password) },
    {
      id: "special",
      label: "One special character",
      passed: /[!@#$%^&*()\-_=+[\]{};:'",.<>/?\\|`~]/.test(password),
    },
  ];
}

export function isPasswordValid(password: string): boolean {
  return checkPasswordRules(password).every((rule) => rule.passed);
}

export type PasswordStrength = "empty" | "weak" | "medium" | "strong";

export function getPasswordStrength(password: string): PasswordStrength {
  if (!password) return "empty";
  const passedCount = checkPasswordRules(password).filter((r) => r.passed).length;
  if (passedCount <= 2) return "weak";
  if (passedCount <= 4) return "medium";
  return "strong";
}

export function isValidEmail(value: string): boolean {
  return EMAIL_REGEX.test(value.trim());
}

export function isValidPhone(value: string): boolean {
  return PHONE_REGEX.test(value.replace(/[\s-]/g, ""));
}

export function isValidUsername(value: string): boolean {
  return USERNAME_REGEX.test(value.trim());
}
