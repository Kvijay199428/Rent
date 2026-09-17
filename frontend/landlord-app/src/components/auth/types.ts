// components/auth/types.ts
import type { ReactNode } from "react";

/** Brand logo: pass an image/svg path as a string, or a ready-made ReactNode (inline SVG, <img>, text). */
export type LogoProp = string | ReactNode;

export interface SocialProvider {
  id: string;
  label: string;
  /** Called when the user clicks this provider's button. */
  onClick: () => void;
  /** Optional custom icon; defaults to the built-in Google mark for id === "google". */
  icon?: ReactNode;
  disabled?: boolean;
}

export interface LoginValues {
  identifier: string; // email, phone, or username
  password: string;
  remember: boolean;
}

export interface SignupValues {
  fullName: string;
  email: string;
  phone: string;
  username: string;
  password: string;
}

export interface AuthFlowProps {
  /** String path (png/svg/jpg) or a ReactNode (inline SVG/text logo). Omit to show the default placeholder. */
  logo?: LogoProp;
  /** Shown next to/under the logo. */
  brandName?: string;
  tagline?: string;
  socialProviders?: SocialProvider[];
  onLogin?: (values: LoginValues) => void | Promise<void>;
  onSignup?: (values: SignupValues) => void | Promise<void>;
  termsContent?: ReactNode;
  privacyContent?: ReactNode;
  /** Inline destructive alert shown at the top of the card (server/auth errors). */
  error?: string;
  /** Called whenever the active tab changes, so callers can sync the URL. */
  onTabChange?: (tab: "login" | "signup") => void;
  defaultTab?: "login" | "signup";
  className?: string;
}
