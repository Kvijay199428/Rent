import { type RefObject } from 'react';
import { useInView, type UseInViewOptions } from 'framer-motion';
import { useRef } from 'react';

interface UseScrollRevealOptions {
  /** Distance to travel from hidden to visible (px) */
  distance?: number;
  /** Duration of the entrance animation (ms) */
  duration?: number;
  /** Delay before animation starts (ms) */
  delay?: number;
  /** Whether to trigger once (true) or on every scroll (false) */
  once?: boolean;
  /** Viewport margin — triggers before element enters viewport */
  margin?: UseInViewOptions['margin'];
  /** Amount of element that must be visible (0-1) */
  amount?: number | 'some' | 'all';
}

interface UseScrollRevealReturn {
  ref: RefObject<HTMLDivElement | null>;
  isInView: boolean;
  motionStyle: {
    opacity: number;
    transform: string;
  };
}

/**
 * Hook that combines framer-motion's useInView with a scroll-reveal pattern.
 * Returns a ref, isInView state, and CSS style object to apply.
 *
 * Usage:
 * ```tsx
 * const { ref, motionStyle } = useScrollReveal();
 * return <div ref={ref} style={motionStyle}>Content</div>;
 * ```
 *
 * For elements that should always be visible (SSR fallback):
 * ```tsx
 * const { ref, motionStyle } = useScrollReveal({ once: true, amount: 0.1 });
 * ```
 */
export function useScrollReveal(
  options: UseScrollRevealOptions = {}
): UseScrollRevealReturn {
  const {
    distance = 20,
    duration = 500,
    delay = 0,
    once = true,
    margin = '-50px',
    amount = 0.1,
  } = options;

  const ref = useRef<HTMLDivElement | null>(null);
  const isInView = useInView(ref, {
    once,
    margin,
    amount,
  });

  const motionStyle = {
    opacity: isInView ? 1 : 0,
    transform: isInView ? 'translateY(0)' : `translateY(${distance}px)`,
    transition: isInView
      ? `opacity ${duration}ms cubic-bezier(0.45, 0, 0.55, 1) ${delay}ms, transform ${duration}ms cubic-bezier(0.45, 0, 0.55, 1) ${delay}ms`
      : 'none',
  };

  return { ref, isInView, motionStyle };
}

/* ── Stagger variant for list children ───────────────────────────────── */

interface UseStaggerRevealOptions extends UseScrollRevealOptions {
  /** Number of children to stagger */
  count: number;
  /** Stagger delay between each child (ms) */
  staggerDelay?: number;
}

/**
 * Hook for staggered list/grid reveals.
 * Returns a parent ref and per-child style array.
 *
 * Usage:
 * ```tsx
 * const { parentRef, childStyles } = useStaggerReveal({ count: items.length });
 * return (
 *   <div ref={parentRef}>
 *     {items.map((item, i) => (
 *       <div key={i} style={childStyles[i]}>{item}</div>
 *     ))}
 *   </div>
 * );
 * ```
 */
export function useStaggerReveal(
  options: UseStaggerRevealOptions
) {
  const {
    count,
    staggerDelay = 60,
    distance = 16,
    duration = 400,
    delay = 0,
    once = true,
    margin = '-40px',
    amount = 0.1,
  } = options;

  const parentRef = useRef<HTMLDivElement | null>(null);
  const isInView = useInView(parentRef, {
    once,
    margin,
    amount,
  });

  const childStyles = Array.from({ length: count }, (_, i) => ({
    opacity: isInView ? 1 : 0,
    transform: isInView ? 'translateY(0)' : `translateY(${distance}px)`,
    transition: isInView
      ? `opacity ${duration}ms cubic-bezier(0.45, 0, 0.55, 1) ${delay + i * staggerDelay}ms, transform ${duration}ms cubic-bezier(0.45, 0, 0.55, 1) ${delay + i * staggerDelay}ms`
      : 'none',
  }));

  return { parentRef, childStyles, isInView };
}
