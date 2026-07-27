/**
 * Sprint 103: Input component (2026 design).
 */
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const inputVariants = cva(
  [
    "flex w-full rounded-md border border-border bg-surface",
    "px-3 py-2 text-base text-fg",
    "placeholder:text-fg-subtle",
    "transition-modern",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500",
    "focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
    "disabled:cursor-not-allowed disabled:opacity-50",
    "file:border-0 file:bg-transparent file:text-sm file:font-medium",
  ].join(" "),
  {
    variants: {
      inputSize: {
        sm: "h-8 text-sm",
        md: "h-10",
        lg: "h-12 text-lg",
      },
      invalid: {
        true: "border-danger focus-visible:ring-danger",
        false: "",
      },
    },
    defaultVariants: {
      inputSize: "md",
      invalid: false,
    },
  }
);

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement>,
    VariantProps<typeof inputVariants> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, inputSize, invalid, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(inputVariants({ inputSize, invalid }), className)}
      {...props}
    />
  )
);
Input.displayName = "Input";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    VariantProps<typeof inputVariants> {}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, inputSize, invalid, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(inputVariants({ inputSize, invalid }), "min-h-20", className)}
      {...props}
    />
  )
);
Textarea.displayName = "Textarea";

export { inputVariants };
