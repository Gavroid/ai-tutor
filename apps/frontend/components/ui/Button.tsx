/**
 * Sprint 103: Button component (2026 design).
 *
 * Variants:
 * - primary: brand accent (default CTA)
 * - secondary: subtle
 * - ghost: text-only
 * - outline: border only
 * - danger: error action
 * - gradient: aurora (special CTAs)
 *
 * Sizes: sm, md, lg, icon
 */
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  // Base styles
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap",
    "font-medium select-none cursor-pointer",
    "transition-modern",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500",
    "focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
    "disabled:pointer-events-none disabled:opacity-50",
    "active:scale-[0.98]",
    "[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  ].join(" "),
  {
    variants: {
      variant: {
        primary: [
          "brand-gradient text-white",
          "shadow-glow hover:shadow-glow-lg",
          "border border-white/20",
        ].join(" "),
        secondary: [
          "bg-white/92 text-[#171022] backdrop-blur",
          "hover:bg-white",
          "border border-brand-300/60 shadow-sm",
        ].join(" "),
        ghost: [
          "bg-transparent text-fg",
          "hover:bg-surface-2",
        ].join(" "),
        outline: [
          "bg-transparent text-fg",
          "border border-border",
          "hover:bg-surface-2",
        ].join(" "),
        danger: [
          "bg-danger text-white",
          "hover:opacity-90",
          "shadow-sm",
        ].join(" "),
        gradient: [
          "brand-gradient",
          "text-white shadow-glow hover:shadow-glow-lg",
          "border border-white/20",
        ].join(" "),
      },
      size: {
        sm: "h-8 px-3 text-sm rounded",
        md: "h-10 px-4 text-base rounded-md",
        lg: "h-12 px-6 text-lg rounded-lg",
        icon: "h-10 w-10 rounded-md",
      },
      fullWidth: {
        true: "w-full",
        false: "",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
      fullWidth: false,
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, fullWidth, loading, children, disabled, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, fullWidth }), className)}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <>
            <span className="inline-block size-4 animate-spin rounded-full border-2 border-current border-r-transparent" />
            {children}
          </>
        ) : (
          children
        )}
      </button>
    );
  }
);
Button.displayName = "Button";

export { buttonVariants };
