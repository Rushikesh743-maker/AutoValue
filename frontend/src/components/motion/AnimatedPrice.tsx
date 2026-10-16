import React, { useEffect, useState } from 'react';
import { useReducedMotion } from 'motion/react';

interface AnimatedPriceProps {
  value: number; // raw value in INR, e.g. 1184000
  formatter?: (val: number) => string;
  className?: string;
  durationMs?: number;
}

export const AnimatedPrice: React.FC<AnimatedPriceProps> = ({
  value,
  formatter,
  className = '',
  durationMs = 350
}) => {
  const shouldReduceMotion = useReducedMotion();
  const [displayValue, setDisplayValue] = useState<number>(() => (shouldReduceMotion ? value : 0));

  const defaultFormat = (v: number) => {
    const lakhs = v / 100000;
    return `₹ ${lakhs.toFixed(2)} Lakh`;
  };

  const formatFn = formatter || defaultFormat;

  useEffect(() => {
    if (shouldReduceMotion) {
      setDisplayValue(value);
      return;
    }

    let startTimestamp: number | null = null;
    const startValue = 0;
    let animationFrameId: number;

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / durationMs, 1);
      // Clean cubic ease-out: 1 - Math.pow(1 - progress, 3)
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(startValue + (value - startValue) * easeOut);
      setDisplayValue(current);

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(step);
      } else {
        setDisplayValue(value);
      }
    };

    animationFrameId = requestAnimationFrame(step);

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [value, durationMs, shouldReduceMotion]);

  return <span className={`num-tabular ${className}`}>{formatFn(displayValue)}</span>;
};
