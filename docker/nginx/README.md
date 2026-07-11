# nginx

## Purpose

This directory holds all NGINX configuration files used by the NGINX container defined in
`docker/docker-compose.yml`. NGINX serves as the single ingress point for the OptiAgent
platform, handling reverse-proxying in development and TLS termination plus static-file
serving in production.

Keeping NGINX configuration here, separate from `docker-compose.yml`, makes it easy to
review routing rules, update upstream addresses, and add new location blocks without
touching the compose file.

## Responsibilities

- Define the main NGINX configuration (`nginx.conf`) including upstream blocks for the
  backend and frontend services.
- Define per-service server blocks (`frontend.conf`) that proxy or serve each application.
- Route `/api` traffic to the Node.js backend at port 8000.
- Route `/` traffic to the React frontend — the Vite dev server at port 3000 in
  development, or the compiled static build directory in production.
- Terminate TLS (HTTPS/WSS) in production and forward plain HTTP internally.

## Does NOT Contain

- TLS certificates or private keys (mount these at runtime via Docker secrets or a
  volume bind).
- Application business logic or any awareness of API endpoint semantics.
- Docker Compose service definitions (those live in `docker/docker-compose.yml`).
- Frontend source code or build artifacts.

## Architecture Position

```
Internet / Developer browser
        │ HTTPS :443 (prod) / HTTP :80 (dev)
        ▼
   NGINX container  (this directory configures it)
        │
        ├─ location /api  → upstream backend  (Node/Express :8000)
        │                   passes X-Forwarded-For, Host headers
        │
        └─ location /     → upstream frontend (Vite dev :3000)  [dev]
                          → root /usr/share/nginx/html           [prod]
                            (pre-built React static files)
```

## Expected Contents

```
nginx/
├── nginx.conf        — top-level config: worker settings, http block,
│                       upstream backend { server backend:8000; }
│                       upstream frontend { server frontend:3000; }
├── frontend.conf     — server block for / proxy or static-file serving;
│                       includes WebSocket upgrade headers for Vite HMR (dev)
└── README.md         — this file
```

## Design Principles

- **Single ingress.** All external traffic enters through NGINX so that auth headers,
  CORS, and rate-limiting are applied in one place.
- **Dev/prod parity.** The same config files are used in both profiles; environment
  differences are handled by compose variable substitution rather than separate config
  trees.
- **Minimal NGINX footprint.** NGINX does only proxying and TLS offload; it does not
  implement caching, gzip, or auth logic that belongs in the application layer.

## Current Status

Implemented

## Future Work

Add HTTPS server block with certificate paths for production TLS. Add WebSocket proxy
headers for the backend once the real-time agent streaming endpoint (Increment 8) is
active. Consider adding rate-limiting `limit_req_zone` directives at the NGINX level as a
first line of defense.
