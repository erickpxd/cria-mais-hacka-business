import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  use: {
    baseURL: 'http://localhost',
    headless: true,
    launchOptions: { executablePath: '/usr/bin/google-chrome' },
  },
})
