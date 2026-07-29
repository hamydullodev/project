import type { PointerEvent } from "react";

/**
 * Spawns one `.ripple-dot` span (see globals.css's `ripple-expand`
 * keyframe) at the pointer's position inside `event.currentTarget` and
 * removes it once the animation finishes.
 *
 * WHY A PLAIN DOM-MUTATING FUNCTION, NOT A REACT-STATE-DRIVEN COMPONENT
 * ------------------------------------------------------------------------
 * A ripple is fire-and-forget visual feedback with no bearing on
 * component state or re-renders — routing it through `useState`/render
 * would mean a state update (and a re-render) on every single click just
 * to draw a decoration that deletes itself 600ms later. Directly
 * mounting/unmounting a DOM node is what the browser's own `:active`
 * pseudo-class effectively does; this is the same idea, just themed.
 * Callers just need `position: relative` and `overflow: hidden` on the
 * element this is attached to (every button it's used on already has
 * rounded corners, so `overflow: hidden` is a wash).
 */
export function spawnRipple(event: PointerEvent<HTMLElement>): void {
  const target = event.currentTarget;
  const rect = target.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height) * 1.6;

  const dot = document.createElement("span");
  dot.className = "ripple-dot";
  dot.style.width = `${size}px`;
  dot.style.height = `${size}px`;
  dot.style.left = `${event.clientX - rect.left - size / 2}px`;
  dot.style.top = `${event.clientY - rect.top - size / 2}px`;

  target.appendChild(dot);
  dot.addEventListener("animationend", () => dot.remove(), { once: true });
}
