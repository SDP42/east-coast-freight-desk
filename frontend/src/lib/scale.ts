import { useEffect, useState } from "react";

/** Current UI scale: the root font size relative to the 16px design baseline. 1 on laptops, about 1.33 on QHD, 2 on 4K screens. */
export const uiScale = (): number => (typeof window === "undefined" ? 1 : parseFloat(getComputedStyle(document.documentElement).fontSize) / 16 || 1);

/** Scales a pixel size (chart heights, axis widths, font sizes) with the rest of the interface. */
export const px = (n: number): number => Math.round(n * uiScale() * 10) / 10;

/** Re-renders the caller whenever the scale changes (window resized across a breakpoint, or moved to another display). */
export function useUiScale(): number {
  const [s, setS] = useState(uiScale);
  useEffect(() => {
    const on = () => setS(uiScale());
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);
  return s;
}
