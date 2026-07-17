/** @type {import('tailwindcss').Config} */
export default {
  // Sprint 5.3: darkMode через class (вместо default 'media').
  // Используется в ThemeToggle — переключатель темы в footer.
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};