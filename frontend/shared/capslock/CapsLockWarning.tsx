import type { CSSProperties } from "react";

interface CapsLockWarningProps {
  isCapsLockOn: boolean;
  style?: CSSProperties;
}

export default function CapsLockWarning({
  isCapsLockOn,
  style,
}: CapsLockWarningProps) {
  if (!isCapsLockOn) return null;

  return (
    <div
      role="alert"
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 8,
        background: "#fef3c7",
        border: "1px solid #f59e0b",
        color: "#92400e",
        borderRadius: 8,
        padding: "10px 14px",
        marginBottom: 14,
        fontSize: 13,
        lineHeight: 1.4,
        fontWeight: 600,
        ...style,
      }}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ flexShrink: 0, marginTop: 1 }}
        aria-hidden="true"
      >
        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
        <path d="M12 9v4" />
        <path d="M12 17h.01" />
      </svg>
      <span>Caps Lock is ON</span>
    </div>
  );
}