import { defineConfig } from 'tsup';
import { resolve } from 'path';

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
  // Path aliases for esbuild to resolve internal imports
  esbuildOptions: (options) => {
    options.alias = {
      '@core/di/types': resolve(__dirname, 'src/core/di/types.ts'),
      '@core/errors/app-error': resolve(__dirname, 'src/core/errors/app-error.ts'),
      '@core/logging/logger': resolve(__dirname, 'src/core/logging/logger.ts'),
      '@core/http/api-response': resolve(__dirname, 'src/core/http/api-response.ts'),
      '@core/http/async-handler': resolve(__dirname, 'src/core/http/async-handler.ts'),
      '@core/auth/department-access-service': resolve(__dirname, 'src/core/auth/department-access-service.ts'),
      '@config/env': resolve(__dirname, 'src/config/env.ts'),
      '@config/constants': resolve(__dirname, 'src/config/constants.ts'),
      '@infrastructure/cache/redis.service': resolve(__dirname, 'src/infrastructure/cache/redis.service.ts'),
      '@infrastructure/database/prisma.service': resolve(__dirname, 'src/infrastructure/database/prisma.service.ts'),
      '@infrastructure/security/jwt.service': resolve(__dirname, 'src/infrastructure/security/jwt.service.ts'),
      '@infrastructure/security/password.service': resolve(__dirname, 'src/infrastructure/security/password.service.ts'),
      '@infrastructure/security/token-store': resolve(__dirname, 'src/infrastructure/security/token-store.ts'),
      '@infrastructure/audit/audit-log.service': resolve(__dirname, 'src/infrastructure/audit/audit-log.service.ts'),
      '@infrastructure/storage/storage.service': resolve(__dirname, 'src/infrastructure/storage/storage.service.ts'),
      '@infrastructure/queue/indexing-queue': resolve(__dirname, 'src/infrastructure/queue/indexing-queue.ts'),
      '@infrastructure/ai/ai-gateway': resolve(__dirname, 'src/infrastructure/ai/ai-gateway.ts'),
      '@middleware/authenticate': resolve(__dirname, 'src/middleware/authenticate.middleware.ts'),
      '@middleware/authorize': resolve(__dirname, 'src/middleware/authorize.middleware.ts'),
      '@middleware/validate': resolve(__dirname, 'src/middleware/validate.middleware.ts'),
      '@middleware/rate-limit': resolve(__dirname, 'src/middleware/rate-limit.middleware.ts'),
      '@middleware/request-id': resolve(__dirname, 'src/middleware/request-id.middleware.ts'),
      '@middleware/request-logger': resolve(__dirname, 'src/middleware/request-logger.middleware.ts'),
      '@middleware/trace-context': resolve(__dirname, 'src/middleware/trace-context.middleware.ts'),
      '@modules/auth': resolve(__dirname, 'src/modules/auth'),
      '@modules/users': resolve(__dirname, 'src/modules/users'),
      '@modules/roles': resolve(__dirname, 'src/modules/roles'),
      '@modules/departments': resolve(__dirname, 'src/modules/departments'),
      '@modules/documents': resolve(__dirname, 'src/modules/documents'),
      '@modules/conversations': resolve(__dirname, 'src/modules/conversations'),
      '@modules/dashboard': resolve(__dirname, 'src/modules/dashboard'),
      '@modules/analytics': resolve(__dirname, 'src/modules/analytics'),
      '@modules/audit-logs': resolve(__dirname, 'src/modules/audit-logs'),
      '@modules/notifications': resolve(__dirname, 'src/modules/notifications'),
      '@modules/admin-settings': resolve(__dirname, 'src/modules/admin-settings'),
    };
  },
});
