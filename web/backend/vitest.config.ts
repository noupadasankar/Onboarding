import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

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
    // Alias for path imports in tests
    alias: {
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
    },
  },
});
