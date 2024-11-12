# Stage 1: Development environment
FROM node:18-alpine AS development

# Set working directory
WORKDIR /app

# Install necessary tools for development
RUN apk add --no-cache git

# Create Next.js project with specific configurations using create-next-app
RUN npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-git --use-yarn

# Install additional dependencies
RUN yarn add -D @types/node autoprefixer postcss tailwindcss \
    && yarn add @radix-ui/react-slot class-variance-authority clsx lucide-react \
    tailwind-merge

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

# Copy necessary files from builder
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Expose the port
EXPOSE 3000

# Set the command to run the app
CMD ["node", "server.js"]

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/ || exit 1

# Add Docker metadata
LABEL version="1.0"
LABEL description="Next.js application with TypeScript and Tailwind"