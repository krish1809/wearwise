import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  // Resolves the "@/" import alias from tsconfig.json.
  resolve: { tsconfigPaths: true },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    // End-to-end tests run in a real browser with Playwright (`pnpm e2e`), not here.
    exclude: ["**/node_modules/**", "e2e/**"],
  },
});
