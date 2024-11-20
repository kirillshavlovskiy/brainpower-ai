# Stage 1: Development environment
FROM node:18-alpine AS development

# Set working directory
WORKDIR /app

# Install necessary tools for development
RUN apk add --no-cache git curl python3 make g++

# Copy package files
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy the rest of the application
COPY . .

# Add build script to package.json
RUN node -e "const pkg=require('./package.json'); pkg.scripts.build='next build'; require('fs').writeFileSync('package.json', JSON.stringify(pkg, null, 2))"

# Stage 2: Production build
FROM node:18-alpine AS builder

WORKDIR /app

# Copy files from development stage
COPY --from=development /app/. .

# Install production dependencies and build
RUN yarn install --production --frozen-lockfile && \
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
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/components/dynamic ./components/dynamic
COPY --from=builder /app/styles/dynamic ./styles/dynamic
COPY --from=builder /app/lib/templates ./lib/templates

# Create volume for dynamic components
VOLUME /app/components/dynamic
VOLUME /app/styles/dynamic
VOLUME /app/public/previews

# Add file watcher script
COPY watch-components.js ./
RUN chmod +x watch-components.js

# Expose ports
EXPOSE 3000
EXPOSE 8000

# Set environment variables
ENV NEXT_TELEMETRY_DISABLED=1
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true

# Start both the Next.js server and file watcher
CMD ["sh", "-c", "node watch-components.js & node server.js"]

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/ || exit 1

# Add Docker metadata
LABEL version="1.0"
LABEL description="Next.js application with TypeScript and Tailwind + Dynamic Component Support"