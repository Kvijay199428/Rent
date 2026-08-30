import type { JSX, ReactNode } from "react";

interface IconProps {
  size?: number;
  "aria-hidden"?: boolean | "true" | "false";
  className?: string;
}

export type IconComponent = (props: IconProps) => JSX.Element;

export function Icon({ size = 24, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`svgi ${props.className ?? ""}`}
      aria-hidden={props["aria-hidden"] ?? true}
    >
      {props.children}
    </svg>
  );
}

export function HomeIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V21h14V9.5" />
      <path d="M9 21v-6h6v6" />
    </Icon>
  );
}

export function UserIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </Icon>
  );
}

export function ShieldIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <path d="M12 3 5 6v6c0 4 3 7 7 9 4-2 7-5 7-9V6l-7-3Z" />
      <path d="m9 12 2 2 4-4" />
    </Icon>
  );
}

export function LockIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <rect x="4" y="11" width="16" height="10" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </Icon>
  );
}

export function ReceiptIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <path d="M5 3h14v18l-3-2-2 2-2-2-2 2-2-2-3 2V3Z" />
      <path d="M9 8h6M9 12h6" />
    </Icon>
  );
}

export function TeamIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <circle cx="9" cy="8" r="4" />
      <path d="M2 21a7 7 0 0 1 14 0" />
      <path d="M16 4a4 4 0 0 1 0 8M22 21a6 6 0 0 0-4-6" />
    </Icon>
  );
}

export function BellIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <path d="M6 9a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </Icon>
  );
}

export function KeyIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <circle cx="8" cy="16" r="4" />
      <path d="m11 13 9-9M16 4l4 4M14 8l3 3" />
    </Icon>
  );
}

export function BuildingIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <path d="M3 21h18M5 21V4h10v17M9 7h2M9 11h2M9 15h2M15 9h2M15 13h2" />
    </Icon>
  );
}

export function ZapIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" />
    </Icon>
  );
}

export function DatabaseIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
      <path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />
    </Icon>
  );
}

export function SpreadsheetIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <rect x="4" y="3" width="16" height="18" />
      <path d="M4 9h16M4 15h16M9 3v18M15 3v18" />
    </Icon>
  );
}

export function FileSearchIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Z" />
      <path d="M14 3v6h6" />
      <circle cx="11" cy="15" r="3" />
      <path d="m13.5 17.5 2 2" />
    </Icon>
  );
}

export function ArrowRightIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </Icon>
  );
}

export function ArrowUpRightIcon({ size = 24, ...p }: IconProps) {
  return (
    <Icon size={size} {...p}>
      <path d="M7 17 17 7M8 7h9v9" />
    </Icon>
  );
}
