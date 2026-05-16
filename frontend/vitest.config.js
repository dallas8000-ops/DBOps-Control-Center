import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.js"],
    include: ["src/**/*.test.{js,jsx}"],
    testTimeout: 30000, // Set a timeout of 30 seconds for each test
    minThreads: 1, // Ensure at least one thread is used
    maxThreads: 2, // Cap thread usage to reduce memory pressure
  },
});