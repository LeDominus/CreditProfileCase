# Dependencies stage — Bun for fast installs
FROM oven/bun:1-slim AS deps
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# Build stage — Node.js 22 for the Next.js 16 build
FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# BACKEND_URL is build-time: rewrites() are frozen into
# dist/routes-manifest.json during `next build`.
ARG BACKEND_URL=http://backend:5555
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build

# Production stage
FROM node:22-slim AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=8502

COPY --from=builder --chown=node:node /app/dist ./dist
COPY --from=builder --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/package.json ./package.json
COPY --from=builder --chown=node:node /app/next.config.ts ./next.config.ts
COPY --from=builder --chown=node:node /app/public ./public

USER node

EXPOSE 8502

CMD ["node", "node_modules/next/dist/bin/next", "start", "-p", "8502"]
