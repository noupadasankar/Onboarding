/**
 * OpenAPI 3 document + Swagger UI mount. Kept as a hand-authored spec for the
 * Increment-1 surface; can be generated from decorators/JSDoc in a later pass.
 */
import type { Express } from 'express';
import swaggerUi from 'swagger-ui-express';
import { API_PREFIX } from '../config/constants';

const openApiDocument = {
  openapi: '3.0.3',
  info: {
    title: 'OptiAgent Backend API',
    version: '0.1.0',
    description: 'Node gateway — authentication, RBAC, users (Increment 1).',
  },
  servers: [{ url: API_PREFIX }],
  components: {
    securitySchemes: {
      bearerAuth: { type: 'http', scheme: 'bearer', bearerFormat: 'JWT' },
    },
    schemas: {
      LoginRequest: {
        type: 'object',
        required: ['email', 'password'],
        properties: {
          email: { type: 'string', format: 'email', example: 'hr.manager@optiagent.dev' },
          password: { type: 'string', example: 'Password123!' },
        },
      },
      RefreshRequest: {
        type: 'object',
        required: ['refreshToken'],
        properties: { refreshToken: { type: 'string' } },
      },
    },
  },
  paths: {
    '/auth/login': {
      post: {
        tags: ['auth'],
        summary: 'Authenticate and receive access + refresh tokens',
        requestBody: {
          required: true,
          content: { 'application/json': { schema: { $ref: '#/components/schemas/LoginRequest' } } },
        },
        responses: { '200': { description: 'Authenticated' }, '401': { description: 'Invalid credentials' } },
      },
    },
    '/auth/refresh': {
      post: {
        tags: ['auth'],
        summary: 'Rotate a refresh token for a new token pair',
        requestBody: {
          required: true,
          content: { 'application/json': { schema: { $ref: '#/components/schemas/RefreshRequest' } } },
        },
        responses: { '200': { description: 'Rotated' }, '401': { description: 'Invalid refresh token' } },
      },
    },
    '/auth/logout': {
      post: {
        tags: ['auth'],
        summary: 'Revoke a refresh token',
        requestBody: {
          required: true,
          content: { 'application/json': { schema: { $ref: '#/components/schemas/RefreshRequest' } } },
        },
        responses: { '200': { description: 'Logged out' } },
      },
    },
    '/auth/me': {
      get: {
        tags: ['auth'],
        summary: 'Current principal from the access token',
        security: [{ bearerAuth: [] }],
        responses: { '200': { description: 'Principal' }, '401': { description: 'Unauthenticated' } },
      },
    },
    '/users': {
      get: {
        tags: ['users'],
        summary: 'List users (requires users:read)',
        security: [{ bearerAuth: [] }],
        parameters: [
          { name: 'page', in: 'query', schema: { type: 'integer', default: 1 } },
          { name: 'pageSize', in: 'query', schema: { type: 'integer', default: 20 } },
        ],
        responses: { '200': { description: 'Paginated users' }, '403': { description: 'Forbidden' } },
      },
    },
  },
} as const;

export function mountSwagger(app: Express): void {
  app.use('/docs', swaggerUi.serve, swaggerUi.setup(openApiDocument));
  app.get('/docs.json', (_req, res) => res.json(openApiDocument));
}
