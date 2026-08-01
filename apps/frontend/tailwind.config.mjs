/** @type {import('tailwindcss').Config} */
// Sprint 103: AI-Tutor 2026 design tokens
// Синхронизировано с globals.css (CSS variables)
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class", // class-based (theme toggle)
  theme: {
    extend: {
      // === Colors (синхронизировано с CSS variables) ===
      colors: {
        brand: {
          50: "#fff1fb",
          100: "#ffe1f6",
          200: "#ffc2ec",
          300: "#ff8fde",
          400: "#ff5dcc",
          500: "#ff2fb3",
          600: "#e31696",
          700: "#bf0d7a",
          800: "#9d0d66",
          900: "#7d1154",
        },
        accent: {
          500: "#ff9f1c",
          600: "#ff7a00",
        },
        surface: {
          DEFAULT: "var(--color-surface)",
          2: "var(--color-surface-2)",
          3: "var(--color-surface-3)",
        },
        fg: {
          DEFAULT: "var(--color-fg)",
          muted: "var(--color-fg-muted)",
          subtle: "var(--color-fg-subtle)",
        },
        border: {
          DEFAULT: "var(--color-border)",
          strong: "var(--color-border-strong)",
        },
        bg: {
          DEFAULT: "var(--color-bg)",
        },
        success: "#14d87a",
        warning: "#ffb000",
        danger: "#ff3b6b",
        info: "#19bfff",
      },

      // === Typography ===
      fontFamily: {
        sans: ["Inter", "Inter Variable", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        display: ["Inter", "Inter Variable", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "SF Mono", "Cascadia Code", "Menlo", "Consolas", "monospace"],
      },

      fontSize: {
        // 2026 scale: tighter line-height, larger display
        "display-2xl": ["4.5rem", { lineHeight: "1.05", letterSpacing: "-0.03em", fontWeight: "700" }],
        "display-xl":  ["3.75rem", { lineHeight: "1.1",  letterSpacing: "-0.025em", fontWeight: "700" }],
        "display-lg":  ["3rem",    { lineHeight: "1.15", letterSpacing: "-0.02em",  fontWeight: "700" }],
        "display-md":  ["2.25rem", { lineHeight: "1.2",  letterSpacing: "-0.015em", fontWeight: "600" }],
        "display-sm":  ["1.875rem",{ lineHeight: "1.25", letterSpacing: "-0.01em",  fontWeight: "600" }],
        // Body
        "lg":          ["1.125rem",{ lineHeight: "1.65", letterSpacing: "-0.011em" }],
        "base":        ["1rem",    { lineHeight: "1.55" }],  // Sprint 11.5: 17px → rem base
        "sm":          ["0.9375rem",{ lineHeight: "1.55" }],
        "xs":          ["0.8125rem",{ lineHeight: "1.5" }],
      },

      // === Spacing (4px base, modern generous) ===
      spacing: {
        "0.5": "2px",
        "1":   "4px",
        "1.5": "6px",
        "2":   "8px",
        "2.5": "10px",
        "3":   "12px",
        "3.5": "14px",
        "4":   "16px",
        "5":   "20px",
        "6":   "24px",
        "7":   "28px",
        "8":   "32px",
        "9":   "36px",
        "10":  "40px",
        "11":  "44px",
        "12":  "48px",
        "14":  "56px",
        "16":  "64px",
        "18":  "72px",
        "20":  "80px",
        "24":  "96px",
        "28":  "112px",
        "32":  "128px",
        "40":  "160px",
        "48":  "192px",
        "56":  "224px",
        "64":  "256px",
      },

      // === Border radius (2026 generous) ===
      borderRadius: {
        none: "0",
        sm: "6px",
        DEFAULT: "10px",
        md: "14px",
        lg: "20px",
        xl: "28px",
        "2xl": "36px",
        "3xl": "48px",
        full: "9999px",
      },

      // === Shadows (subtle, layered) ===
      boxShadow: {
        xs: "0 1px 2px 0 rgb(0 0 0 / 0.04)",
        sm: "0 1px 2px 0 rgb(0 0 0 / 0.06), 0 1px 3px 0 rgb(0 0 0 / 0.04)",
        DEFAULT: "0 2px 4px -1px rgb(0 0 0 / 0.06), 0 4px 8px -2px rgb(0 0 0 / 0.04)",
        md: "0 4px 12px -2px rgb(0 0 0 / 0.08), 0 8px 24px -4px rgb(0 0 0 / 0.06)",
        lg: "0 12px 32px -8px rgb(0 0 0 / 0.10), 0 24px 64px -16px rgb(0 0 0 / 0.08)",
        xl: "0 24px 48px -12px rgb(0 0 0 / 0.15)",
        "2xl": "0 32px 64px -16px rgb(0 0 0 / 0.20)",
        glow: "0 0 0 1px rgb(99 102 241 / 0.10), 0 4px 16px -2px rgb(99 102 241 / 0.20)",
        "glow-lg": "0 0 0 1px rgb(99 102 241 / 0.20), 0 8px 32px -4px rgb(99 102 241 / 0.30)",
        inner: "inset 0 2px 4px 0 rgb(0 0 0 / 0.06)",
      },

      // === Motion (2026 smooth, opt-out) ===
      transitionTimingFunction: {
        "out-expo": "cubic-bezier(0.16, 1, 0.3, 1)",
        "in-out-expo": "cubic-bezier(0.65, 0, 0.35, 1)",
        "spring": "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
      transitionDuration: {
        DEFAULT: "220ms",
        fast: "150ms",
        slow: "320ms",
        slower: "500ms",
      },

      // === Background images (2026 trends) ===
      backgroundImage: {
        "aurora":
          "radial-gradient(at 27% 37%, rgba(255, 47, 179, 0.24) 0px, transparent 50%), radial-gradient(at 97% 21%, rgba(25, 246, 255, 0.16) 0px, transparent 50%), radial-gradient(at 52% 99%, rgba(255, 138, 31, 0.16) 0px, transparent 50%)",
        "vice-city":
          "radial-gradient(circle at 18% 18%, rgba(255, 47, 179, 0.38), transparent 26rem), radial-gradient(circle at 82% 12%, rgba(25, 246, 255, 0.24), transparent 25rem), linear-gradient(135deg, #120725 0%, #251252 45%, #5b1b69 72%, #ff7a1a 135%)",
        "dots": "radial-gradient(circle, rgb(0 0 0 / 0.10) 1px, transparent 1px)",
        "grid":
          "linear-gradient(to right, rgb(0 0 0 / 0.04) 1px, transparent 1px), linear-gradient(to bottom, rgb(0 0 0 / 0.04) 1px, transparent 1px)",
      },

      // === Z-index scale ===
      zIndex: {
        "dropdown": "100",
        "sticky":   "200",
        "overlay":  "300",
        "modal":    "400",
        "popover":  "500",
        "toast":     "600",
        "tooltip":   "700",
      },
    },
  },
  plugins: [],
};
