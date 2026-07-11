# syntax=docker/dockerfile:1
# Build context is the repo root (see docker/docker-compose.yml).
FROM node:20-alpine AS build
RUN npm install -g pnpm@8.15.9
WORKDIR /app
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY shared/package.json ./shared/
COPY frontend/package.json ./frontend/
RUN pnpm install --filter @optiagent/frontend... || true
COPY tsconfig.base.json ./
COPY shared ./shared
COPY frontend ./frontend
RUN pnpm --filter @optiagent/shared build && pnpm --filter @optiagent/frontend build

FROM nginx:alpine AS runtime
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY docker/nginx/frontend.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
