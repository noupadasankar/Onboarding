# Backend Architecture

OptiAgent — Node.js API Gateway

---

## Table of Contents

1. [Request Pipeline Layering](#request-pipeline-layering)
2. [Module Structure](#module-structure)
3. [Dependency Injection with InversifyJS](#dependency-injection-with-inversifyjs)
4. [RBAC: Permission-Based Authorization](#rbac-permission-based-authorization)
5. [Audit Logging](#audit-logging)
6. [JWT RS256 and Refresh Token Rotation](#jwt-rs256-and-refresh-token-rotation)

---

## Request Pipeline Layering

Every HTTP request passes through a fixed middleware chain before reaching business logic. The layers are applied in the following order:

```
Incoming HTTP Request
        │
        ▼
┌───────────────────┐
│   requestId       │  Assigns a UUID correlation ID. Sets X-Request-ID on req and res.
└────────┬──────────┘
         ▼
┌───────────────────┐
│   requestLogger   │  Logs method, URL, correlation ID, and response time.
└────────┬──────────┘
         ▼
┌───────────────────┐
│   authenticate    │  Validates JWT RS256 signature and expiry. Populates req.auth.
└────────┬──────────┘
         ▼
┌───────────────────┐
│   authorize       │  Checks req.auth.permissions[] for the required permission string.
└────────┬──────────┘
         ▼
┌───────────────────┐
│   validate        │  Runs Zod schema against req.body / req.query / req.params.
└────────┬──────────┘
         ▼
┌───────────────────┐
│   Controller      │  Extracts validated data. Calls the appropriate service method.
└────────┬──────────┘
         ▼
┌───────────────────┐
│   Service         │  Contains business logic. Calls repositories and other services.
└────────┬──────────┘
         ▼
┌───────────────────┐
│   Repository      │  Data-access interface. Implemented by a Prisma concrete class.
└────────┬──────────┘
         ▼
┌───────────────────┐
│   Prisma Client   │  Type-safe ORM. Executes SQL against PostgreSQL.
└───────────────────┘
```

Each layer has a single responsibility. Controllers never call Prisma directly. Services never inspect HTTP headers. Repositories never contain business logic.

### Error Flow

Any layer can throw a typed `AppError` (subclasses: `UnauthorizedError`, `ForbiddenError`, `NotFoundError`, `ValidationError`, `ConflictError`). A global Express error handler intercepts these, maps them to HTTP status codes, and formats the response using the shared `ApiResponse` envelope. Unhandled errors produce a sanitized 500 response; internal details are logged but never sent to the client.

---

## Module Structure

The backend is organized by domain. Each domain module follows a three-layer internal structure:

```
src/
├── modules/
│   ├── auth/
│   │   ├── domain/
│   │   │   ├── auth.types.ts          # Interfaces, DTOs, value objects
│   │   │   └── auth.errors.ts         # Domain-specific error subtypes
│   │   ├── application/
│   │   │   ├── auth.service.ts        # Business logic (IAuthService interface + impl)
│   │   │   └── auth.controller.ts     # HTTP layer: extract → call service → respond
│   │   └── infrastructure/
│   │       ├── auth.repository.ts     # IAuthRepository interface + PrismaAuthRepository
│   │       ├── auth.routes.ts         # Express router: mount middleware, controller
│   │       └── auth.module.ts         # InversifyJS bindings for this domain
│   │
│   ├── users/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   │
│   └── ... (documents, ai — planned)
│
├── shared/
│   ├── middleware/                    # requestId, requestLogger, authenticate, authorize
│   ├── errors/                        # AppError hierarchy
│   ├── types/                         # ApiResponse<T>, PaginatedResponse<T>
│   └── utils/
│
├── container.ts                       # Root InversifyJS container wiring all modules
└── app.ts                             # Express app: mount routers, error handler
```

### Layer Responsibilities

**domain/** — Pure TypeScript. Defines interfaces, DTOs, and value objects. Has zero runtime dependencies (no Express, no Prisma, no InversifyJS). This is the stable core that other layers depend on.

**application/** — Business logic. Services implement the interfaces defined in domain/. They are injected with repository interfaces (not concrete classes) so they remain testable. Controllers are thin HTTP adapters that call service methods.

**infrastructure/** — Framework code. Prisma repository implementations, Express route definitions, and the InversifyJS module binding file for the domain.

---

## Dependency Injection with InversifyJS

InversifyJS provides an IoC container that wires concrete implementations to their interfaces at startup.

### Symbol Tokens

Each injectable type is identified by a Symbol, defined in a central `TYPES` object to avoid string collisions:

```typescript
// src/shared/types/injection-tokens.ts
export const TYPES = {
  // Auth
  IAuthService: Symbol.for('IAuthService'),
  IAuthRepository: Symbol.for('IAuthRepository'),
  ITokenService: Symbol.for('ITokenService'),

  // Users
  IUserService: Symbol.for('IUserService'),
  IUserRepository: Symbol.for('IUserRepository'),

  // Cross-cutting
  IAuditService: Symbol.for('IAuditService'),
  IRedisClient: Symbol.for('IRedisClient'),
  IPrismaClient: Symbol.for('IPrismaClient'),
} as const;
```

### Module Binding Pattern

Each domain module exports a ContainerModule that binds its types:

```typescript
// src/modules/auth/infrastructure/auth.module.ts
import { ContainerModule } from 'inversify';
import { TYPES } from '../../../shared/types/injection-tokens';
import { AuthService } from '../application/auth.service';
import { PrismaAuthRepository } from './auth.repository';
import { TokenService } from '../application/token.service';

export const authModule = new ContainerModule((bind) => {
  bind(TYPES.IAuthService).to(AuthService).inSingletonScope();
  bind(TYPES.IAuthRepository).to(PrismaAuthRepository).inSingletonScope();
  bind(TYPES.ITokenService).to(TokenService).inSingletonScope();
});
```

### Root Container

The root container loads all domain modules and shared infrastructure:

```typescript
// src/container.ts
import { Container } from 'inversify';
import { authModule } from './modules/auth/infrastructure/auth.module';
import { usersModule } from './modules/users/infrastructure/users.module';
import { sharedModule } from './shared/shared.module';

const container = new Container();
container.load(sharedModule, authModule, usersModule);

export { container };
```

### Constructor Injection

Services and controllers declare their dependencies via `@inject` decorators:

```typescript
@injectable()
export class AuthService implements IAuthService {
  constructor(
    @inject(TYPES.IAuthRepository) private readonly authRepo: IAuthRepository,
    @inject(TYPES.ITokenService)   private readonly tokenSvc: ITokenService,
    @inject(TYPES.IAuditService)   private readonly auditSvc: IAuditService,
  ) {}
}
```

---

## RBAC: Permission-Based Authorization

Authorization is enforced at the permission level, not the role level. This distinction is deliberate: roles change over time, but permissions represent stable capabilities.

### Permission Strings

Permissions follow a `resource:action` naming convention:

```
users:read       users:write      users:delete
roles:read       roles:write
permissions:read permissions:write
ai:query
audit:read
```

### Resolved at Login

When a user authenticates, the backend:

1. Loads the user's assigned roles from the database.
2. Loads the permissions associated with each role.
3. Deduplicates and sorts the permission strings.
4. Embeds the full permission set in the JWT payload as `permissions: string[]`.

No permission lookup is needed on subsequent requests — the JWT carries the resolved set.

### Enforcement

The `authorize` middleware factory returns a middleware that checks `req.auth.permissions`:

```typescript
// Usage on a route
router.get(
  '/',
  authenticate,
  authorize('users:read'),
  validate(listUsersSchema),
  controller.listUsers,
);
```

```typescript
// Middleware implementation (simplified)
export function authorize(requiredPermission: string): RequestHandler {
  return (req, res, next) => {
    if (!req.auth?.permissions.includes(requiredPermission)) {
      throw new ForbiddenError('Insufficient permissions.');
    }
    next();
  };
}
```

### Role Names

The set of valid role names is defined in the shared package (`@optiagent/shared`), not the database:

```typescript
export const Roles = {
  ADMIN:            'ADMIN',
  HR_MANAGER:       'HR_MANAGER',
  FINANCE_MANAGER:  'FINANCE_MANAGER',
  IT_MANAGER:       'IT_MANAGER',
  EMPLOYEE:         'EMPLOYEE',
} as const;
```

This eliminates a round-trip on every request and ensures role names are validated at compile time. What varies per deployment — which permissions each role holds — remains in the database.

---

## Audit Logging

Audit logging is a cross-cutting concern implemented as a non-fatal injectable service.

### Audit Record Structure

```typescript
interface AuditRecord {
  actorId:    string;       // User performing the action
  action:     string;       // e.g. 'USER_CREATED', 'ROLE_ASSIGNED'
  targetType: string;       // e.g. 'User', 'Role'
  targetId:   string;       // ID of the affected entity
  meta?:      object;       // Optional additional context
  ipAddress?: string;
  requestId?: string;       // Correlation ID from X-Request-ID
  createdAt:  Date;
}
```

### Non-Fatal Pattern

The `AuditService` wraps every write in a try-catch. A failure to write an audit record is logged at WARN level but never rethrown. Business operations are never blocked by an audit side-effect.

```typescript
@injectable()
export class AuditService implements IAuditService {
  constructor(
    @inject(TYPES.IPrismaClient) private readonly prisma: PrismaClient,
  ) {}

  async log(record: AuditRecord): Promise<void> {
    try {
      await this.prisma.auditLog.create({ data: record });
    } catch (err) {
      // Audit failure must never surface to the caller.
      logger.warn('Audit log write failed', { error: err, record });
    }
  }
}
```

### Usage in Services

```typescript
// Inside UserService.createUser()
const user = await this.userRepo.create(data);

// Fire-and-forget — no await needed; failure is caught internally.
this.auditSvc.log({
  actorId:    context.userId,
  action:     'USER_CREATED',
  targetType: 'User',
  targetId:   user.id,
  requestId:  context.requestId,
  ipAddress:  context.ipAddress,
});

return user;
```

---

## JWT RS256 and Refresh Token Rotation

### Key Pair

Authentication uses asymmetric RS256 signing:

- The **private key** is held only by the Node.js backend and used to sign JWTs.
- The **public key** can be distributed to any service (e.g., the Python AI service) that needs to verify tokens without being able to issue them.

Keys are loaded from environment variables at startup, never from the filesystem in production images.

### Access Token

```
Algorithm:  RS256
Expiry:     15 minutes
Payload:    { sub: userId, email, permissions: string[], iat, exp }
```

The short expiry limits the blast radius of a stolen token. The `permissions` claim eliminates per-request database lookups.

### Refresh Token

```
Storage:    Redis (key: refreshToken → userId, TTL: 7 days)
Format:     Cryptographically random opaque string (UUID v4)
Rotation:   Every use — old token is revoked, new token issued
```

### Refresh Token Rotation Flow

```
1. Client sends POST /auth/refresh with { refreshToken: "<current>" }.

2. Backend looks up the token in Redis.
   - If not found: the token has been used, expired, or revoked.
     Return 401 Unauthorized. (Potential replay detected.)

3. Backend atomically:
   a. Deletes the current refresh token from Redis.
   b. Generates a new access token (RS256, 15 min).
   c. Generates a new refresh token (random, opaque).
   d. Stores the new refresh token in Redis with a 7-day TTL.

4. Returns { accessToken, refreshToken } to the client.
```

Rotation means each refresh token can only be used once. If an attacker replays a stolen refresh token after the legitimate client has already used it, the Redis lookup will fail and the attempt is rejected.

### Logout

On logout, the client sends the current refresh token to `POST /auth/logout`. The backend deletes it from Redis immediately. Any subsequent use of that token returns 401.
