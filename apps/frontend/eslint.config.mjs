// Sprint 3.24 (Этап 2.2 плана 13-*.md): ESLint flat config для Next.js 16 + TS.
// Раньше гейт был только `tsc --noEmit` + pytest. Теперь добавлен `npm run lint`.
//
// Решение: НЕ используем eslint-config-next — он тянет legacy eslint-plugin-react@7.37
// который конфликтует с ESLint v10 API (context.getFilename). Используем прямой
// typescript-eslint preset + базовые React rules вручную. После Sprint 3.24
// baseline можно будет добавить scoped Next.js rules через @next/eslint-plugin-next.

import js from "@eslint/js";
import globals from "globals";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";

export default [
  // Глобальные игноры
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "next-env.d.ts",
      "e2e/**",  // Playwright specs — отдельный scope
      "messages/**",  // i18n — generated
      "public/sw.js",  // Service Worker — браузерный ctx (self/fetch/caches)
      "*.config.mjs",
      "*.config.ts",
      "scripts/**",
    ],
  },

  // Базовый JS preset
  js.configs.recommended,

  // TypeScript rules
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
    },
    rules: {
      // TypeScript recommended rules
      ...tsPlugin.configs.recommended.rules,

      // Sprint 3.24 baseline-ignore: легаси от спринтов 1-100, постепенно
      // уменьшаем список по мере починки. Каждое правило ниже документировано.
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-empty-function": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
      "@typescript-eslint/no-empty-object-type": "off",

      // Sprint 3.24: react-hooks/exhaustive-deps — плагин отдельно не
      // установлен (eslint-config-next@16 с react@7 конфликтует с v10).
      // Sprint 3.25+: добавим @eslint-react/eslint-plugin-react-hooks.
      // eslint-disable-next-line/react-hooks директивы в коде подавляются,
      // чтобы ESLint не жаловался "rule not found".
      "react-hooks/exhaustive-deps": "off",
      "report-unused-disable-directives": "off",

      // no-undef: отключён для .tsx/.ts — TypeScript сам ловит types,
      // а для globals (self/fetch/caches/RequestInit/React) мы покрываем
      // через globals package + ts-plugin.
      "no-undef": "off",

      // no-empty: WS/chat/AI handlers содержат ожидающие try { } catch {}
      // для стабильности pipeline (progress/spaced etc.). Пустые блоки
      // безвредны и переписывать их сейчас — scope creep.
      "no-empty": "warn",

      // no-misleading-character-class: один regex в lib/markdown.ts
      // содержит emoji range, который eslint 10 трактует как «suspect
      // homoglyph». Это false positive — character class — умышленный.
      "no-misleading-character-class": "off",

      // Общие JS-preset rules
      "no-console": ["warn", { allow: ["warn", "error", "info", "log", "debug"] }],
      "no-debugger": "warn",
      "prefer-const": "warn",
      "no-unused-vars": "off", // отдан TS-eslint настройке выше
    },
  },

  // Test files: console.log допустим для диагностики
  {
    files: ["**/*.test.ts", "**/*.test.tsx"],
    rules: {
      "no-console": "off",
    },
  },
];
