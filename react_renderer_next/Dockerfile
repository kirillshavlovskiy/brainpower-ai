# Stage 1: Development environment
FROM node:18-alpine AS development

# Set working directory
WORKDIR /app

# Install necessary tools for development
RUN apk add --no-cache git curl python3 make g++

# Create Next.js project with specific configurations using create-next-app
RUN npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-git --use-yarn

# Install additional dependencies for dynamic component editing
RUN yarn add -D \
    @types/node \
    autoprefixer \
    postcss \
    tailwindcss \
    @types/react-dom \
    @types/react-syntax-highlighter \
    typescript \
    prettier \
    eslint-config-prettier

# Install runtime dependencies
RUN yarn add \
    @radix-ui/react-slot \
    class-variance-authority \
    clsx \
    lucide-react \
    tailwind-merge \
    framer-motion \
    react-syntax-highlighter \
    @monaco-editor/react \
    monaco-editor \
    @babel/parser \
    @babel/traverse \
    @babel/generator \
    @babel/types \
    chokidar \
    ws

# Create necessary directories for dynamic components
RUN mkdir -p /app/components/dynamic \
    /app/styles/dynamic \
    /app/lib/templates \
    /app/public/previews

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