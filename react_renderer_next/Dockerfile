# Development environment
FROM node:18-alpine

WORKDIR /app

# Install necessary tools and configure environment
RUN apk add --no-cache git curl python3 make g++ && \
    yarn config set network-timeout 600000 && \
    yarn config set network-concurrency 1 && \
    yarn config set registry https://registry.npmjs.org/

# Copy package files first
COPY package.json ./

# Install dependencies with improved error handling and logging
RUN touch yarn.lock && \
    for i in 1 2 3; do \
      echo "Attempt $i/3 to install dependencies..." && \
      yarn install --network-timeout 600000 --prefer-offline \
        --ignore-optional \
        --ignore-engines \
        --ignore-platform \
        --no-progress \
        --silent \
        2>&1 | grep -v "warning" || \
      { \
        echo "Retry $i/3 failed. Waiting before retry..." && \
        sleep 30; \
        continue; \
      }; \
      echo "Dependencies installed successfully!" && break; \
    done

# Create necessary directories
RUN mkdir -p /app/src/app \
    /app/components/dynamic \
    /app/styles/dynamic \
    /app/lib/templates \
    /app/public/previews

# Copy configuration files
COPY next.config.js ./
COPY tsconfig.json ./
COPY tailwind.config.ts ./
COPY postcss.config.mjs ./

# Create default .env.local
RUN echo "DOCKER_HOST=localhost\n\
DOCKER_PORT=3001\n\
NEXT_PUBLIC_API_URL=http://localhost:3001\n\
NEXT_PUBLIC_DOCKER_API_URL=http://localhost:3001\n\
WATCHPACK_POLLING=true\n\
CHOKIDAR_USEPOLLING=true" > .env.local

# Copy source files
COPY src ./src
COPY components ./components
COPY lib ./lib
COPY public ./public
COPY styles ./styles
COPY watch-components.js ./

# Set proper permissions
RUN chown -R node:node /app && \
    chmod -R 755 /app

# Create volume for dynamic content
VOLUME /app/components/dynamic
VOLUME /app/styles/dynamic
VOLUME /app/public/previews

# Expose port 3001 for Next.js
EXPOSE 3001

# Switch to non-root user
USER node

# Set environment variables
ENV NEXT_TELEMETRY_DISABLED=1
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true
ENV NODE_ENV=development
ENV PORT=3001
ENV HOST=0.0.0.0
ENV NODE_OPTIONS="--max-old-space-size=8192"

# Start development server
CMD ["sh", "-c", "PORT=3001 yarn dev & node watch-components.js"]