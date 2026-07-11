# Deployment Architecture

OptiAgent — Infrastructure and Docker Compose

---

## Table of Contents

1. [Service Topology](#service-topology)
2. [Docker Compose Services](#docker-compose-services)
3. [Port Assignments](#port-assignments)
4. [NGINX Reverse Proxy](#nginx-reverse-proxy)
5. [Environment Variables](#environment-variables)
6. [Production Considerations](#production-considerations)

---

## Service Topology

All OptiAgent services run as Docker containers connected through an internal bridge network (`optiagent-network`). The only service exposed to the host machine is NGINX, which acts as the single public entry point.

```
                    ┌─────────────────────────────────────────────┐
                    │               Host Machine                  │
                    │                                             │
                    │   Browser → localhost:80 (or :443 prod)     │
                    └─────────────────────┬───────────────────────┘
                                          │
                    ┌─────────────────────▼───────────────────────┐
                    │            optiagent-network (Docker)        │
                    │                                             │
                    │  ┌─────────────────────────────────────┐   │
                    │  │            NGINX                    │   │
                    │  │      (public: :80, :443)            │   │
                    │  └──────┬────────────────┬─────────────┘   │
                    │         │                │                  │
                    │         ▼                ▼                  │
                    │  ┌────────────┐  ┌──────────────────┐      │
                    │  │  Backend   │  │    Frontend       │      │
                    │  │  Node.js   │  │ (static files     │      │
                    │  │  :8000     │  │  served by NGINX) │      │
                    │  └──────┬─────┘  └──────────────────┘      │
                    │         │                                   │
                    │    ┌────┴──────────────────┐               │
                    │    │                       │               │
                    │    ▼                       ▼               │
                    │  ┌──────────┐    ┌──────────────────┐      │
                    │  │ Postgres │    │   AI Service     │      │
                    │  │   :5432  │    │   FastAPI :8100  │      │
                    │  └──────────┘    └────────┬─────────┘      │
                    │                           │                │
                    │  ┌──────────┐    ┌────────▼─────────┐      │
                    │  │  Redis   │    │    ChromaDB      │      │
                    │  │   :6379  │    │     :8200        │      │
                    │  └──────────┘    └──────────────────┘      │
                    │                                             │
                    └─────────────────────────────────────────────┘
```

The backend accesses PostgreSQL and Redis. The AI service accesses PostgreSQL (its own schema) and ChromaDB. No service directly accesses another service's primary database — cross-service communication is always via HTTP.

---

## Docker Compose Services

The `docker-compose.yml` at the project root defines the following services:

### postgres

```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_DB:       optiagent
    POSTGRES_USER:     ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - postgres_data:/var/lib/postgresql/data
  networks:
    - optiagent-network
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
    interval: 10s
    timeout: 5s
    retries: 5
```

### redis

```yaml
redis:
  image: redis:7-alpine
  command: redis-server --requirepass ${REDIS_PASSWORD}
  volumes:
    - redis_data:/data
  networks:
    - optiagent-network
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 3s
    retries: 5
```

### chromadb

```yaml
chromadb:
  image: chromadb/chroma:latest
  volumes:
    - chroma_data:/chroma/chroma
  networks:
    - optiagent-network
```

### backend

```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile
  env_file: ./backend/.env
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  networks:
    - optiagent-network
```

The backend runs `prisma migrate deploy && node dist/server.js` as its entrypoint. It does not expose a port to the host — all traffic reaches it through NGINX.

### ai-service

```yaml
ai-service:
  build:
    context: ./ai-service
    dockerfile: Dockerfile
  env_file: ./ai-service/.env
  depends_on:
    postgres:
      condition: service_healthy
    chromadb:
      condition: service_started
  networks:
    - optiagent-network
```

The AI service runs `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8100` as its entrypoint.

### nginx

```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./frontend/dist:/usr/share/nginx/html:ro
    - ./nginx/certs:/etc/nginx/certs:ro
  depends_on:
    - backend
    - ai-service
  networks:
    - optiagent-network
```

---

## Port Assignments

| Service | Internal Port | Host-Exposed | Notes |
|---|---|---|---|
| NGINX | 80, 443 | 80, 443 | Only service exposed to host |
| Frontend (static) | — | — | Served directly by NGINX from `/usr/share/nginx/html` |
| Backend (Node.js) | 8000 | No | Internal only; reached via NGINX proxy |
| AI Service (FastAPI) | 8100 | No | Internal only; reached via Node.js backend |
| PostgreSQL | 5432 | No | Internal only |
| Redis | 6379 | No | Internal only |
| ChromaDB | 8200 | No | Internal only; reached via AI service |

In development, individual services may expose ports to the host for direct access during debugging. These are disabled in production compose profiles.

---

## NGINX Reverse Proxy

NGINX serves two purposes: it proxies API traffic to the Node.js backend, and it serves the React frontend's static build output.

### nginx.conf (Simplified)

```nginx
upstream backend {
  server backend:8000;
}

server {
  listen 80;
  server_name _;

  # API traffic → Node.js backend
  location /api/ {
    proxy_pass         http://backend;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
    proxy_set_header   X-Request-ID      $request_id;
  }

  # All other traffic → React SPA
  location / {
    root       /usr/share/nginx/html;
    try_files  $uri $uri/ /index.html;
  }
}
```

### HTTPS (Production)

In production, NGINX terminates TLS. The HTTP server block redirects to HTTPS:

```nginx
server {
  listen 80;
  return 301 https://$host$request_uri;
}

server {
  listen 443 ssl;
  ssl_certificate     /etc/nginx/certs/optiagent.crt;
  ssl_certificate_key /etc/nginx/certs/optiagent.key;
  ssl_protocols       TLSv1.2 TLSv1.3;
  ssl_ciphers         HIGH:!aNULL:!MD5;
  # ... location blocks same as above
}
```

### Why NGINX (Not a Node.js Proxy)

- Serving static files from NGINX is significantly more efficient than serving them from a Node.js process (no JavaScript runtime overhead per file).
- NGINX handles TLS termination, connection pooling, and gzip compression without adding application-layer complexity.
- Separating static file serving from API logic means the backend process handles only API requests.

---

## Environment Variables

Each service has its own `.env` file. A corresponding `.env.example` file is committed to the repository with placeholder values. Actual `.env` files are gitignored and must be created locally or injected by the deployment pipeline.

### backend/.env.example

```
# Database
DATABASE_URL=postgresql://optiagent:changeme@postgres:5432/optiagent

# Redis
REDIS_URL=redis://:changeme@redis:6379

# JWT
JWT_PRIVATE_KEY_PATH=/run/secrets/jwt_private_key
JWT_PUBLIC_KEY_PATH=/run/secrets/jwt_public_key
JWT_ACCESS_EXPIRY=900          # seconds (15 min)
JWT_REFRESH_EXPIRY=604800      # seconds (7 days)

# Internal service token (shared with AI service)
INTERNAL_SERVICE_TOKEN=changeme

# AI service
AI_SERVICE_URL=http://ai-service:8100

# App
NODE_ENV=production
PORT=8000
LOG_LEVEL=info
```

### ai-service/.env.example

```
# Database (AI service schema)
AI_DATABASE_URL=postgresql://optiagent:changeme@postgres:5432/optiagent

# ChromaDB
AI_CHROMA_HOST=chromadb
AI_CHROMA_PORT=8200

# Anthropic
AI_ANTHROPIC_API_KEY=sk-ant-changeme

# Internal service token (must match backend)
AI_INTERNAL_SERVICE_TOKEN=changeme

# App
AI_LOG_LEVEL=info
AI_PORT=8100
```

---

## Production Considerations

### TLS Termination

TLS is terminated at NGINX. All traffic inside the Docker network is plain HTTP. This is acceptable because the Docker internal network is not accessible from outside the host, and all containers trust each other within the network boundary. In a cloud deployment (Kubernetes, ECS), mutual TLS (mTLS) between services should be considered.

### Secrets Management

In production, secrets must not be stored in `.env` files on the host filesystem. The recommended approach:

- Use Docker secrets (Swarm) or a secrets manager (AWS Secrets Manager, HashiCorp Vault) to inject secrets at runtime.
- The JWT private key should never appear as a plain string in an environment variable — mount it as a file and reference the path.
- The `INTERNAL_SERVICE_TOKEN` should be rotated periodically and injected from a secrets store.

### Image Security

- No secrets are baked into Docker images at build time. All sensitive values come from the runtime environment.
- Node.js and Python images use non-root users in production Dockerfiles.
- Base images are pinned to specific digest hashes in production to prevent unexpected upstream changes.

### Health Checks and Restart Policies

All services define Docker health checks. NGINX and the backend depend on their upstream services being healthy before starting. Compose restart policies are set to `unless-stopped` in production to recover from transient failures.

### Database Backups

PostgreSQL data is stored in a named Docker volume (`postgres_data`). In production, this volume must be backed up on a schedule. The recommended approach is a nightly `pg_dump` piped to encrypted object storage (S3, Azure Blob).
