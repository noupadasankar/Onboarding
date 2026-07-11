/**
 * Generates an RS256 keypair for JWT signing/verification.
 * Windows-safe: uses Node's crypto, no openssl dependency.
 *
 *   node backend/scripts/generate-keys.mjs
 *
 * Writes backend/secrets/jwt-private.pem and jwt-public.pem (gitignored).
 */
import { generateKeyPairSync } from 'node:crypto';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const secretsDir = resolve(here, '..', 'secrets');
const privatePath = resolve(secretsDir, 'jwt-private.pem');
const publicPath = resolve(secretsDir, 'jwt-public.pem');

if (existsSync(privatePath) && !process.argv.includes('--force')) {
  console.log('Keys already exist. Re-run with --force to overwrite.');
  process.exit(0);
}

const { privateKey, publicKey } = generateKeyPairSync('rsa', {
  modulusLength: 2048,
  publicKeyEncoding: { type: 'spki', format: 'pem' },
  privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
});

mkdirSync(secretsDir, { recursive: true });
writeFileSync(privatePath, privateKey, { mode: 0o600 });
writeFileSync(publicPath, publicKey, { mode: 0o644 });

console.log('RS256 keypair written to backend/secrets/:');
console.log('  - jwt-private.pem (keep secret)');
console.log('  - jwt-public.pem');
