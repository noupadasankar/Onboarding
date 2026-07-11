# syntax=docker/dockerfile:1
# Multi-stage build for the Node/Express gateway.
# Note: build context is the repo root (see docker/docker-compose.yml) so the
# shared workspace package is available.

FROM node:20-alpine AS base
RUN npm install -g pnpm@8.15.9
WORKDIR /app

# --- Install deps (workspace-aware) ---
FROM base AS deps
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY shared/package.json ./shared/
COPY backend/package.json ./backend/
RUN pnpm install --filter @optiagent/backend... --frozen-lockfile || pnpm install --filter @optiagent/backend...

# --- Build ---
FROM deps AS build
COPY tsconfig.base.json ./
COPY shared ./shared
COPY backend ./backend
RUN pnpm --filter @optiagent/shared build \
 && pnpm --filter @optiagent/backend prisma:generate \
 && pnpm --filter @optiagent/backend build

# --- Runtime ---
FROM base AS runtime
ENV NODE_ENV=production
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/shared/dist ./shared/dist
COPY --from=build /app/shared/package.json ./shared/
COPY --from=build /app/backend/dist ./backend/dist
COPY --from=build /app/backend/node_modules ./backend/node_modules
COPY --from=build /app/backend/prisma ./backend/prisma
COPY --from=build /app/backend/package.json ./backend/
WORKDIR /app/backend
EXPOSE 8000
CMD ["node", "dist/main.js"]
