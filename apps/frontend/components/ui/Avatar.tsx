/**
 * Sprint 103: Avatar component (2026 design).
 *
 * Fallback to initials if no image. Color by hash of name.
 */
import * as React from "react";
import { cn } from "@/lib/utils";

const sizeClasses = {
  sm: "size-8 text-xs",
  md: "size-10 text-sm",
  lg: "size-12 text-base",
  xl: "size-16 text-lg",
};

const colorPalettes = [
  "bg-brand-500",
  "bg-accent-500",
  "bg-success",
  "bg-warning",
  "bg-info",
  "bg-pink-500",
  "bg-purple-500",
  "bg-cyan-500",
];

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  name: string;
  src?: string;
  size?: keyof typeof sizeClasses;
  alt?: string;
}

export const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(
  ({ className, name, src, size = "md", alt, ...props }, ref) => {
    const initials = getInitials(name);
    const color = colorPalettes[hashString(name) % colorPalettes.length];
    const [imgError, setImgError] = React.useState(false);

    if (src && !imgError) {
      return (
        <div
          ref={ref}
          className={cn(
            "relative inline-flex items-center justify-center overflow-hidden rounded-full",
            sizeClasses[size],
            className
          )}
          {...props}
        >
          <img
            src={src}
            alt={alt || name}
            onError={() => setImgError(true)}
            className="size-full object-cover"
          />
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-full font-semibold text-white",
          color,
          sizeClasses[size],
          className
        )}
        aria-label={name}
        {...props}
      >
        {initials || "?"}
      </div>
    );
  }
);
Avatar.displayName = "Avatar";
