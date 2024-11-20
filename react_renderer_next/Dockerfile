# Development environment
FROM node:18-alpine

WORKDIR /app

# Install necessary tools
RUN apk add --no-cache git curl python3 make g++

# Configure yarn for better network handling
RUN yarn config set network-timeout 300000 && \
    yarn config set network-concurrency 4 && \
    yarn config set registry https://registry.npmjs.org/

# Copy package files first
COPY package.json ./

# Install ALL dependencies (including devDependencies)
RUN touch yarn.lock && \
    for i in 1 2 3; \
    do yarn install && break || \
    echo "Retry $i/3..." && \
    sleep 15; \
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

# Create default .env.local if it doesn't exist
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

# Copy watch script
COPY watch-components.js ./

# Set proper permissions
RUN chown -R node:node /app && \
    chmod -R 755 /app

# Create volume for dynamic content
VOLUME /app/components/dynamic
VOLUME /app/styles/dynamic
VOLUME /app/public/previews

# Expose port 3001 (will be mapped to dynamic host port)
EXPOSE 3001

# Switch to non-root user
USER node

# Set environment variables
ENV NEXT_TELEMETRY_DISABLED=1
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true

# Start development server on port 3001
CMD ["sh", "-c", "PORT=3001 yarn dev & node watch-components.js"]