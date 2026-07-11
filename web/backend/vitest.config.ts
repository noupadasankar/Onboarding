import { defineConfig } from 'vitest/config';

export default defineConfig({
  esbuild: {
    // Enable decorator syntax for InversifyJS under esbuild-powered Vitest.
    target: 'es2022',
  },
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/**/*.spec.ts'],
    setupFiles: ['reflect-metadata'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.ts'],
    },
  },
});
