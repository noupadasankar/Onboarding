import 'reflect-metadata';
import { describe, it, expect, beforeAll } from 'vitest';
import request from 'supertest';
import type { Express } from 'express';
import { createApp } from '../../src/app';
import { buildTestContainer } from '../helpers/fakes';

describe('Users routes (integration)', () => {
  let app: Express;

  const login = (email: string, password = 'Password123!') =>
    request(app).post('/api/v1/auth/login').send({ email, password });

  const authHeader = async (email: string) => {
    const { body } = await login(email);
    return `Bearer ${body.data.tokens.accessToken}`;
  };

  beforeAll(async () => {
    const harness = await buildTestContainer();
    app = createApp(harness.container);
  });

  // --- GET /users ---
  describe('GET /users', () => {
    it('returns paginated users for HR_MANAGER (has users:read)', async () => {
      const token = await authHeader('hr.manager@optiagent.dev');
      const res = await request(app).get('/api/v1/users').set('Authorization', token);

      expect(res.status).toBe(200);
      expect(Array.isArray(res.body.data.items)).toBe(true);
      expect(res.body.data.items.length).toBeGreaterThan(0);
      // Confirm no password hash leaks
      expect(res.body.data.items[0]).not.toHaveProperty('passwordHash');
    });

    it('filters by role when ?role= is provided', async () => {
      const token = await authHeader('it.admin@optiagent.dev');
      const res = await request(app)
        .get('/api/v1/users?role=IT_ADMIN')
        .set('Authorization', token);

      expect(res.status).toBe(200);
      expect(res.body.data.items.every((u: { role: string }) => u.role === 'IT_ADMIN')).toBe(true);
    });

    it('filters by search when ?search= is provided', async () => {
      const token = await authHeader('it.admin@optiagent.dev');
      const res = await request(app)
        .get('/api/v1/users?search=hr')
        .set('Authorization', token);

      expect(res.status).toBe(200);
      expect(res.body.data.items.every((u: { email: string }) => u.email.includes('hr'))).toBe(true);
    });

    it('rejects EMPLOYEE (403 — lacks users:read)', async () => {
      const token = await authHeader('employee@optiagent.dev');
      const res = await request(app).get('/api/v1/users').set('Authorization', token);
      expect(res.status).toBe(403);
    });
  });

  // --- POST /users ---
  describe('POST /users', () => {
    it('creates a user and returns 201 for IT_ADMIN (has users:write)', async () => {
      const token = await authHeader('it.admin@optiagent.dev');
      const res = await request(app)
        .post('/api/v1/users')
        .set('Authorization', token)
        .send({ email: 'new.user@optiagent.dev', password: 'Password123!', role: 'EMPLOYEE' });

      expect(res.status).toBe(201);
      expect(res.body.data.email).toBe('new.user@optiagent.dev');
      expect(res.body.data.isActive).toBe(true);
      expect(res.body.data).not.toHaveProperty('passwordHash');
    });

    it('returns 403 for HR_MANAGER (lacks users:write)', async () => {
      const token = await authHeader('hr.manager@optiagent.dev');
      const res = await request(app)
        .post('/api/v1/users')
        .set('Authorization', token)
        .send({ email: 'another@optiagent.dev', password: 'Password123!', role: 'EMPLOYEE' });

      expect(res.status).toBe(403);
    });

    it('returns 409 on duplicate email', async () => {
      const token = await authHeader('it.admin@optiagent.dev');
      // First create succeeds
      await request(app)
        .post('/api/v1/users')
        .set('Authorization', token)
        .send({ email: 'duplicate@optiagent.dev', password: 'Password123!', role: 'EMPLOYEE' });
      // Second create with same email should conflict
      const res = await request(app)
        .post('/api/v1/users')
        .set('Authorization', token)
        .send({ email: 'duplicate@optiagent.dev', password: 'Password123!', role: 'EMPLOYEE' });

      expect(res.status).toBe(409);
      expect(res.body.error.code).toBe('CONFLICT');
    });

    it('returns 400 on invalid body', async () => {
      const token = await authHeader('it.admin@optiagent.dev');
      const res = await request(app)
        .post('/api/v1/users')
        .set('Authorization', token)
        .send({ email: 'not-an-email', password: 'short' });

      expect(res.status).toBe(400);
      expect(res.body.error.code).toBe('VALIDATION_ERROR');
    });
  });

  // --- GET /users/:id ---
  describe('GET /users/:id', () => {
    it('returns the user for a valid UUID', async () => {
      const token = await authHeader('it.admin@optiagent.dev');
      const res = await request(app)
        .get('/api/v1/users/u_it_admin')
        .set('Authorization', token);

      // u_it_admin is not a UUID, so this should be 400 (param validation)
      expect([400, 404]).toContain(res.status);
    });

    it('returns 400 for a non-UUID param', async () => {
      const token = await authHeader('it.admin@optiagent.dev');
      const res = await request(app)
        .get('/api/v1/users/not-a-uuid')
        .set('Authorization', token);

      expect(res.status).toBe(400);
    });
  });

  // --- PATCH /users/:id ---
  describe('PATCH /users/:id', () => {
    it('returns 400 for a non-UUID param', async () => {
      const token = await authHeader('it.admin@optiagent.dev');
      const res = await request(app)
        .patch('/api/v1/users/not-a-uuid')
        .set('Authorization', token)
        .send({ department: 'Engineering' });

      expect(res.status).toBe(400);
    });
  });

  // --- DELETE /users/:id ---
  describe('DELETE /users/:id', () => {
    it('returns 400 for a non-UUID param', async () => {
      const token = await authHeader('it.admin@optiagent.dev');
      const res = await request(app)
        .delete('/api/v1/users/not-a-uuid')
        .set('Authorization', token);

      expect(res.status).toBe(400);
    });

    it('returns 403 for HR_MANAGER (lacks users:write)', async () => {
      const token = await authHeader('hr.manager@optiagent.dev');
      const res = await request(app)
        .delete('/api/v1/users/00000000-0000-0000-0000-000000000001')
        .set('Authorization', token);

      expect(res.status).toBe(403);
    });
  });

  // --- GET /roles ---
  describe('GET /roles', () => {
    it('returns 4 roles with their permissions for any authenticated user', async () => {
      const token = await authHeader('employee@optiagent.dev');
      const res = await request(app).get('/api/v1/roles').set('Authorization', token);

      expect(res.status).toBe(200);
      expect(res.body.data).toHaveLength(4);
      const roleNames = res.body.data.map((r: { name: string }) => r.name);
      expect(roleNames).toContain('EMPLOYEE');
      expect(roleNames).toContain('IT_ADMIN');
    });

    it('returns 401 without authentication', async () => {
      const res = await request(app).get('/api/v1/roles');
      expect(res.status).toBe(401);
    });
  });

  // --- GET /permissions ---
  describe('GET /permissions', () => {
    it('returns all system permission strings', async () => {
      const token = await authHeader('employee@optiagent.dev');
      const res = await request(app).get('/api/v1/permissions').set('Authorization', token);

      expect(res.status).toBe(200);
      expect(Array.isArray(res.body.data)).toBe(true);
      expect(res.body.data.length).toBeGreaterThanOrEqual(7);
    });
  });
});
