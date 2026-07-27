// Sprint 103: shadcn-style utils (cn function).
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * cn — classnames helper with Tailwind merge.
 * Combines clsx() для conditional classes + twMerge() для dedup Tailwind.
 *
 * Usage:
 *   <div className={cn("p-4", isActive && "bg-brand-500", className)} />
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
