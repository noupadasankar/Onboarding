import { defineConfig } from 'tsup';

/**
 * Bundles the ESM server. esbuild handles `experimentalDecorators`; the code uses
 * explicit `@inject(TYPES.x)` tokens everywhere, so runtime DI never depends on
 * `emitDecoratorMetadata`.
 */
export default defineConfig({
  entry: ['src/main.ts'],
  format: ['esm'],
  target: 'node20',
  platform: 'node',
  sourcemap: true,
  clean: true,
  dts: false,
  // Prisma client + native-ish deps stay external (resolved from node_modules at runtime).
  external: ['@prisma/client'],
});
