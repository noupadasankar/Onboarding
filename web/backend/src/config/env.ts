/**
 * Environment configuration — validated once at boot with Zod. If anything is
 * missing or malformed the process exits immediately (fail-fast), so the app
 * never runs in a half-configured state.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { z } from 'zod';

const csv = (value: string): string[] =>
  value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  BACKEND_PORT: z.coerce.number().int().positive().default(8000),
  LOG_LEVEL: z
    .enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace', 'silent'])
    .default('info'),

  DATABASE_URL: z.string().url(),
  REDIS_URL: z.string().url(),

  JWT_PRIVATE_KEY_PATH: z.string().min(1),
  JWT_PUBLIC_KEY_PATH: z.string().min(1),
  JWT_ACCESS_TTL_SECONDS: z.coerce.number().int().positive().default(900),
  JWT_REFRESH_TTL_SECONDS: z.coerce.number().int().positive().default(604800),
  JWT_ISSUER: z.string().min(1).default('optiagent'),
  JWT_AUDIENCE: z.string().min(1).default('optiagent-clients'),

  CORS_ORIGINS: z.string().default('http://localhost:3000'),

  LOGIN_RATE_LIMIT_MAX: z.coerce.number().int().positive().default(5),
  LOGIN_RATE_LIMIT_WINDOW_SECONDS: z.coerce.number().int().positive().default(900),

  AI_SERVICE_URL: z.string().url().default('http://localhost:8100'),
  INTERNAL_SERVICE_TOKEN: z.string().min(1),
});

export interface AppConfig {
  nodeEnv: 'development' | 'test' | 'production';
  isProduction: boolean;
  port: number;
  logLevel: string;
  databaseUrl: string;
  redisUrl: string;
  jwt: {
    privateKey: string;
    publicKey: string;
    accessTtlSeconds: number;
    refreshTtlSeconds: number;
    issuer: string;
    audience: string;
  };
  corsOrigins: string[];
  loginRateLimit: { max: number; windowSeconds: number };
  aiService: { url: string; internalToken: string };
}

let cached: AppConfig | null = null;

/** Parse + validate process.env into a typed, immutable config (memoized). */
export function loadConfig(): AppConfig {
  if (cached) return cached;

  const parsed = envSchema.safeParse(process.env);
  if (!parsed.success) {
    const issues = parsed.error.issues
      .map((i) => `  - ${i.path.join('.')}: ${i.message}`)
      .join('\n');
    // eslint-disable-next-line no-console
    console.error(`Invalid environment configuration:\n${issues}`);
    process.exit(1);
  }

  const e = parsed.data;
  cached = {
    nodeEnv: e.NODE_ENV,
    isProduction: e.NODE_ENV === 'production',
    port: e.BACKEND_PORT,
    logLevel: e.LOG_LEVEL,
    databaseUrl: e.DATABASE_URL,
    redisUrl: e.REDIS_URL,
    jwt: {
      privateKey: readKey(e.JWT_PRIVATE_KEY_PATH),
      publicKey: readKey(e.JWT_PUBLIC_KEY_PATH),
      accessTtlSeconds: e.JWT_ACCESS_TTL_SECONDS,
      refreshTtlSeconds: e.JWT_REFRESH_TTL_SECONDS,
      issuer: e.JWT_ISSUER,
      audience: e.JWT_AUDIENCE,
    },
    corsOrigins: csv(e.CORS_ORIGINS),
    loginRateLimit: {
      max: e.LOGIN_RATE_LIMIT_MAX,
      windowSeconds: e.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    },
    aiService: { url: e.AI_SERVICE_URL, internalToken: e.INTERNAL_SERVICE_TOKEN },
  };
  return cached;
}

function readKey(path: string): string {
  try {
    return readFileSync(resolve(process.cwd(), path), 'utf8');
  } catch {
    // eslint-disable-next-line no-console
    console.error(
      `Unable to read JWT key at "${path}". Run: node scripts/generate-keys.mjs`,
    );
    process.exit(1);
  }
}
