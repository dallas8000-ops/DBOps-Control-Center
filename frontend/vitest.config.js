import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.js"],
    include: ["src/**/*.test.{js,jsx}"],
    testTimeout: 15000,
    hookTimeout: 15000,
    teardownTimeout: 10000,
    pool: "forks",
    maxWorkers: 1,
    fileParallelism: false,
    isolate: true,
  },
});