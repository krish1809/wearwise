import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier/flat";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Formatting is Prettier's job; this turns off the lint rules that would fight it.
  prettier,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Written by Playwright when it runs.
    "test-results/**",
    "playwright-report/**",
    // Generated from the backend's OpenAPI schema.
    "lib/api/schema.d.ts",
  ]),
]);

export default eslintConfig;
