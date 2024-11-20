# Stage 1: Development environment
FROM node:18-alpine AS development

WORKDIR /app

# Install necessary tools
RUN apk add --no-cache git curl python3 make g++

# Copy configuration files first
COPY package.json ./
COPY next.config.ts ./
COPY tsconfig.json ./
COPY tailwind.config.ts ./
COPY postcss.config.mjs ./

# Create yarn.lock and install dependencies
RUN touch yarn.lock && \
    yarn install

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p /app/components/dynamic \
    /app/styles/dynamic \
    /app/lib/templates \
    /app/public/previews

# Stage 2: Production build
FROM node:18-alpine AS builder

WORKDIR /app
COPY --from=development /app/. .
RUN yarn install --frozen-lockfile && \
    yarn build

# Stage 3: Production runtime
FROM node:18-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

# Copy necessary files
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/components/dynamic ./components/dynamic

# Create volumes for dynamic content
VOLUME /app/components/dynamic
VOLUME /app/styles/dynamic
VOLUME /app/public/previews

# Add file watcher
COPY watch-components.js ./
RUN chmod +x watch-components.js

# Expose ports
EXPOSE 3000

# Environment variables
ENV NEXT_TELEMETRY_DISABLED=1
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true

# Start both Next.js and file watcher
CMD ["sh", "-c", "node watch-components.js & node server.js"]