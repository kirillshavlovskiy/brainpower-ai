# Stage 1: Development environment
FROM node:18-alpine AS development

# Set working directory
WORKDIR /app

# Install necessary tools for development
RUN apk add --no-cache git curl python3 make g++

# Create necessary directories
RUN mkdir -p /app/src/app \
    /app/components/dynamic \
    /app/styles/dynamic \
    /app/lib/templates \
    /app/public/previews

# Copy configuration files first
COPY package.json ./
COPY next.config.js ./
COPY tsconfig.json ./
COPY tailwind.config.ts ./
COPY postcss.config.mjs ./

# Configure yarn and install dependencies
RUN yarn config set network-timeout 300000 && \
    yarn config set network-concurrency 4 && \
    yarn config set registry https://registry.npmjs.org/ && \
    yarn install

# Copy source files
COPY src ./src
COPY components ./components
COPY lib ./lib
COPY public ./public
COPY styles ./styles

# Copy other necessary files
COPY watch-components.js ./
COPY .env.local ./

# Stage 2: Production build
FROM node:18-alpine AS builder

WORKDIR /app

# Copy files from development stage
COPY --from=development /app/. .

# Install dependencies and build
RUN yarn install --frozen-lockfile && \
    yarn build

# Stage 3: Production runtime
FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Install runtime system dependencies
RUN apk add --no-cache \
    curl \
    python3 \
    make \
    g++ \
    git

# Copy necessary files from builder
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/components/dynamic ./components/dynamic
COPY --from=builder /app/styles/dynamic ./styles/dynamic
COPY --from=builder /app/lib/templates ./lib/templates
COPY --from=builder /app/watch-components.js ./

# Create volume for dynamic components
VOLUME /app/components/dynamic
VOLUME /app/styles/dynamic
VOLUME /app/public/previews

# Set proper permissions
RUN chown -R node:node /app && \
    chmod -R 755 /app

# Expose ports
EXPOSE 3000
EXPOSE 8000

# Set environment variables
ENV NEXT_TELEMETRY_DISABLED=1
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true

# Switch to non-root user
USER node

# Start both the Next.js server and file watcher
CMD ["sh", "-c", "node watch-components.js & node server.js"]

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/ || exit 1