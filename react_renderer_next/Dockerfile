# Use slim version for smaller image size
FROM node:18-slim

WORKDIR /app

# Install only essential tools with cleanup in same layer
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy package files
COPY package.json ./

# Install dependencies in a single layer with cleanup
RUN yarn install \
    --production \
    --frozen-lockfile \
    --network-timeout 600000 \
    --ignore-optional \
    --ignore-platform \
    --no-progress \
    && yarn cache clean

# Create necessary directories
RUN mkdir -p \
    /app/components/dynamic \
    /app/components/ui \
    /app/src/app \
    /app/src/lib \
    /app/styles

# Copy configuration and source files
COPY components.json tailwind.config.ts postcss.config.js watch-components.js next.config.js tsconfig.json ./
COPY src/app/globals.css ./src/app/
COPY src/app/layout.tsx ./src/app/
COPY src/app/page.tsx ./src/app/
COPY components ./components
COPY styles ./styles
COPY lib ./lib

# Set proper permissions
RUN chown -R node:node /app && \
    chmod -R 755 /app

# Create volumes for dynamic content
VOLUME [ "/app/components/dynamic", "/app/components/ui", "/app/src" ]

# Expose port 3001
EXPOSE 3001

# Switch to non-root user
USER node

# Set essential environment variables with resource limits
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=development \
    PORT=3001 \
    HOST=0.0.0.0 \
    WATCHPACK_POLLING=true \
    CHOKIDAR_USEPOLLING=true \
    NEXT_WEBPACK_POLLING=1000 \
    NEXT_HMR_POLLING_INTERVAL=1000 \
    NODE_OPTIONS="--max-old-space-size=512"

# Start with resource constraints
CMD ["sh", "-c", "WATCHPACK_POLLING=true yarn dev --port 3001 & CHOKIDAR_USEPOLLING=true node watch-components.js"]