FROM node:24-alpine

WORKDIR /app
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

COPY package.json pnpm-workspace.yaml turbo.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/client/package.json packages/client/package.json
COPY packages/ui/package.json packages/ui/package.json
RUN pnpm install --no-frozen-lockfile --config.node-linker=hoisted

COPY . .
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["node", "/app/node_modules/next/dist/bin/next", "dev", "-H", "0.0.0.0", "-p", "3000"]
