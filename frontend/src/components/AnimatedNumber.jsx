import { useState, useEffect, useRef } from 'react';

/**
 * AnimatedNumber — Premium Count-Up Animation Component
 *
 * Smooth, cubic-bezier ease-out count-up animation that triggers when entering the viewport.
 * Features:
 * - requestAnimationFrame with custom ease-out curve (fast start, gradual deceleration)
 * - Viewport trigger via IntersectionObserver (runs once)
 * - Staggered delay support
 * - Integer & Decimal precision preservation
 * - Number formatting (e.g. 18,500) with stable prefix/suffix
 * - Settling micro-animation on completion
 * - Accessibility: prefers-reduced-motion immediate reveal
 */
export default function AnimatedNumber({
  value,
  prefix = '',
  suffix = '',
  duration,
  delay = 0,
  decimals,
  format = true,
  className = '',
  style = {},
}) {
  const numValue = typeof value === 'number' ? value : parseFloat(value) || 0;
  const isDecimal = !Number.isInteger(numValue);
  const precision = decimals !== undefined ? decimals : isDecimal ? (numValue.toString().split('.')[1]?.length || 1) : 0;

  // Determine optimal duration based on number magnitude if not specified
  const effectiveDuration = duration || (numValue > 1000 ? 2200 : numValue > 50 ? 1700 : 1300);

  const [displayValue, setDisplayValue] = useState(0);
  const [hasStarted, setHasStarted] = useState(false);
  const [isSettled, setIsSettled] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    // Check user preference for reduced motion
    if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setDisplayValue(numValue);
      setIsSettled(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !hasStarted) {
          setHasStarted(true);
        }
      },
      { threshold: 0.15, rootMargin: '0px 0px -20px 0px' }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, [hasStarted, numValue]);

  useEffect(() => {
    if (!hasStarted) return;

    let rafId = null;
    let timeoutId = null;

    timeoutId = setTimeout(() => {
      const startTime = performance.now();

      // Custom Quartic Ease-Out curve for rapid start and smooth gentle deceleration
      const easeOutQuart = (t) => 1 - Math.pow(1 - t, 4);

      const updateCounter = (currentTime) => {
        const elapsed = currentTime - startTime;
        const rawProgress = Math.min(elapsed / effectiveDuration, 1);
        const easedProgress = easeOutQuart(rawProgress);

        const currentVal = easedProgress * numValue;
        setDisplayValue(currentVal);

        if (rawProgress < 1) {
          rafId = requestAnimationFrame(updateCounter);
        } else {
          setDisplayValue(numValue);
          setIsSettled(true);
        }
      };

      rafId = requestAnimationFrame(updateCounter);
    }, delay);

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [hasStarted, numValue, effectiveDuration, delay]);

  // Format the numerical output
  const formatNumber = (val) => {
    if (precision > 0) {
      const fixed = val.toFixed(precision);
      if (format) {
        const [intPart, decPart] = fixed.split('.');
        const formattedInt = parseInt(intPart, 10).toLocaleString('en-US');
        return `${formattedInt}.${decPart}`;
      }
      return fixed;
    }
    const rounded = Math.round(val);
    return format ? rounded.toLocaleString('en-US') : rounded.toString();
  };

  return (
    <span
      ref={containerRef}
      className={`animated-number-container ${isSettled ? 'settled' : 'counting'} ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'baseline',
        fontVariantNumeric: 'tabular-nums',
        letterSpacing: '-0.02em',
        transition: 'transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.22s ease-out',
        transform: isSettled ? 'translateY(0) scale(1)' : 'translateY(0) scale(0.995)',
        opacity: hasStarted ? 1 : 0.85,
        ...style,
      }}
    >
      {prefix && <span className="number-prefix">{prefix}</span>}
      <span className="number-digits">{formatNumber(displayValue)}</span>
      {suffix && <span className="number-suffix">{suffix}</span>}
    </span>
  );
}
