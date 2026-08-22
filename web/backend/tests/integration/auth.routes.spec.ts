import 'reflect-metadata';
import { describe, it, expect, beforeAll } from 'vitest';
import request from 'supertest';
import type { Express } from 'express';
import { createApp } from '../../src/app';
import { buildTestContainer } from '../helpers/fakes';

/**
 * Drives the real Express pipeline (middleware + DI + security services) against
 * in-memory infra fakes. Asserts the auth flow, RBAC enforcement, and rotation.
 */
describe('Auth + RBAC routes (integration)', () => {
  let app: Express;

  beforeAll(async () => {
    const harness = await buildTestContainer();
    app = createApp(harness.container);
  });

  const login = (email: string, password = 'Password123!') =>
    request(app).post('/api/v1/auth/login').send({ email, password });

  it('logs in with valid credentials and returns a token pair', async () => {
    const res = await login('hr.manager@optiagent.dev');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.tokens.accessToken).toBeTruthy();
    expect(res.body.data.tokens.refreshToken).toBeTruthy();
    expect(res.body.data.user.role).toBe('HR_MANAGER');
  });

  it('rejects invalid credentials with 401', async () => {
    const res = await login('hr.manager@optiagent.dev', 'WrongPassword123!');
    expect(res.status).toBe(401);
    expect(res.body.error.code).toBe('INVALID_CREDENTIALS');
  });

  it('rejects a malformed body with 400 + field details', async () => {
    const res = await request(app).post('/api/v1/auth/login').send({ email: 'x' });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('VALIDATION_ERROR');
    expect(res.body.error.details).toBeDefined();
  });

  it('returns the principal from GET /auth/me with a valid token', async () => {
    const { body } = await login('hr.manager@optiagent.dev');
    const res = await request(app)
      .get('/api/v1/auth/me')
      .set('Authorization', `Bearer ${body.data.tokens.accessToken}`);
    expect(res.status).toBe(200);
    expect(res.body.data.email).toBe('hr.manager@optiagent.dev');
  });

  it('rejects GET /users without a token (401)', async () => {
    const res = await request(app).get('/api/v1/users');
    expect(res.status).toBe(401);
  });

  it('allows GET /users for HR_MANAGER (has users:read)', async () => {
    const { body } = await login('hr.manager@optiagent.dev');
    const res = await request(app)
      .get('/api/v1/users')
      .set('Authorization', `Bearer ${body.data.tokens.accessToken}`);
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.data.items)).toBe(true);
  });

  it('forbids GET /users for EMPLOYEE (403 — lacks users:read)', async () => {
    const { body } = await login('employee@optiagent.dev');
    const res = await request(app)
      .get('/api/v1/users')
      .set('Authorization', `Bearer ${body.data.tokens.accessToken}`);
    expect(res.status).toBe(403);
    expect(res.body.error.code).toBe('FORBIDDEN');
  });

  it('rotates refresh tokens: the old token cannot be reused', async () => {
    const { body } = await login('employee@optiagent.dev');
    const first = body.data.tokens.refreshToken;

    const rotated = await request(app).post('/api/v1/auth/refresh').send({ refreshToken: first });
    expect(rotated.status).toBe(200);

    const reuse = await request(app).post('/api/v1/auth/refresh').send({ refreshToken: first });
    expect(reuse.status).toBe(401);
  });

  it('invalidates the refresh token on logout', async () => {
    const { body } = await login('employee@optiagent.dev');
    const refreshToken = body.data.tokens.refreshToken;

    await request(app).post('/api/v1/auth/logout').send({ refreshToken }).expect(200);
    const res = await request(app).post('/api/v1/auth/refresh').send({ refreshToken });
    expect(res.status).toBe(401);
  });
});
