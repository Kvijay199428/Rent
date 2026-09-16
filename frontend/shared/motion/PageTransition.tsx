import { type ReactNode } from 'react';
import { useLocation } from 'react-router';

interface PageTransitionProps {
  children: ReactNode;
  className?: string;
}

/**
 * Page-transition wrapper for react-router apps.
 *
 * Keyed by pathname so navigating between routes remounts the subtree and
 * replays the entrance. Uses a deterministic pure-CSS animation
 * (motion-fade-up) instead of a JS animation driver, so content can never be
 * left invisible if JS-based motion fails or the OS requests reduced motion —
 * the animation always ends at opacity 1 / translateY(0).
 */
export function PageTransition({ children, className }: PageTransitionProps) {
  const location = useLocation();

  return (
    <div
      key={location.pathname}
      className={`motion-fade-up${className ? ` ${className}` : ''}`}
    >
      {children}
    </div>
  );
}