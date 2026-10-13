import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";

const python =
  process.env.MATAPAN_TEST_PYTHON ||
  fileURLToPath(
    new URL(
      process.platform === "win32"
        ? "../backend/.venv/Scripts/python.exe"
        : "../backend/.venv/bin/python",
      import.meta.url,
    ),
  );

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:5174",
    trace: "retain-on-failure",
    // Reuse the installed Edge browser on Windows; no separate download needed.
    channel: process.platform === "win32" ? "msedge" : "chromium",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "mobile",
      use: { ...devices["Pixel 7"], defaultBrowserType: "chromium" },
    },
  ],
  webServer: [
    {
      command: `"${python}" tests/serve_backend.py`,
      url: "http://127.0.0.1:8001/health",
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: "npm run dev -- --port 5174",
      url: "http://127.0.0.1:5174",
      env: { MATAPAN_API_TARGET: "http://127.0.0.1:8001" },
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
});
