#!/usr/bin/env node
/**
 * Production database migration script.
 *
 * Usage:
 *   node scripts/migrate-production.mjs
 *
 * This script:
 * 1. Validates environment (must be production)
 * 2. Runs `prisma migrate deploy` (safe for production - no schema drift)
 * 3. Verifies migration success
 * 4. Exits with appropriate code for CI/CD
 */

import { execSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = resolve(fileURLToPath(import.meta.url), '..');
const projectRoot = resolve(__dirname, '..');

function run(cmd: string, options = {}) {
  console.log(`$ ${cmd}`);
  try {
    execSync(cmd, { stdio: 'inherit', cwd: projectRoot, ...options });
  } catch (err) {
    console.error(`❌ Command failed: ${cmd}`);
    process.exit(1);
  }
}

async function main() {
  console.log('🚀 Starting production database migration...\n');

  // 1. Validate environment
  const nodeEnv = process.env.NODE_ENV || 'development';
  if (nodeEnv !== 'production') {
    console.warn(`⚠️  NODE_ENV is "${nodeEnv}", not "production".`);
    console.warn('   This script is designed for production deployments.');
    if (!process.argv.includes('--force')) {
      console.error('   Aborting. Use --force to override.');
      process.exit(1);
    }
  }

  // 2. Validate DATABASE_URL
  if (!process.env.DATABASE_URL) {
    console.error('❌ DATABASE_URL environment variable is required');
    process.exit(1);
  }

  // 3. Verify Prisma schema exists
  const schemaPath = resolve(projectRoot, 'prisma', 'schema.prisma');
  if (!existsSync(schemaPath)) {
    console.error(`❌ Prisma schema not found at ${schemaPath}`);
    process.exit(1);
  }

  // 4. Generate Prisma Client (ensures compatibility)
  console.log('\n📦 Generating Prisma Client...');
  run('npx prisma generate');

  // 5. Check migration status
  console.log('\n📋 Checking migration status...');
  try {
    execSync('npx prisma migrate status', { stdio: 'pipe', cwd: projectRoot });
  } catch {
    // migrate status returns non-zero if there are pending migrations
    console.log('   Pending migrations detected.');
  }

  // 6. Run migrations (deploy mode - safe for production)
  console.log('\n⬆️  Applying migrations (prisma migrate deploy)...');
  run('npx prisma migrate deploy');

  // 7. Verify database connection and schema
  console.log('\n✅ Verifying database connection...');
  run('npx prisma db execute --stdin <<< "SELECT 1"', { shell: true });

  // 8. Optional: Run seed if SEED_PRODUCTION=true
  if (process.env.SEED_PRODUCTION === 'true') {
    console.log('\n🌱 Running production seed...');
    run('npx prisma db seed');
  }

  console.log('\n🎉 Production migration completed successfully!');
}

main().catch((err) => {
  console.error('❌ Migration failed:', err);
  process.exit(1);
});