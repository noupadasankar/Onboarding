/**
 * Structured logger (Pino). No `console.log` anywhere in application code — this
 * is the single logging surface, injected via the DI container.
 */
import pino, { type Logger } from 'pino';
import type { AppConfig } from '../../config/env';

export type { Logger };

export function createLogger(config: AppConfig): Logger {
  return pino({
    level: config.logLevel,
    // Redact anything that could carry secrets/PII out of logs.
    redact: {
      paths: [
        'req.headers.authorization',
        'req.headers.cookie',
        'req.body.password',
        '*.password',
        '*.passwordHash',
        '*.accessToken',
        '*.refreshToken',
      ],
      remove: true,
    },
    base: { service: 'backend' },
    transport: config.isProduction
      ? undefined
      : { target: 'pino-pretty', options: { colorize: true, translateTime: 'SYS:HH:MM:ss' } },
  });
}
