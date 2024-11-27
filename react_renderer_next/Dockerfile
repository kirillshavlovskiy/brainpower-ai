# Use slim version for smaller image size
FROM node:18-slim

WORKDIR /app

# Install only essential tools and clean up in the same layer
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Create all necessary directories
RUN mkdir -p /app/components/dynamic \
    /app/src/app \
    /app/src/lib \
    /app/components/ui \
    /app/components/reusable-components \
    && chown -R 1000:1000 /app && \
    chmod -R 755 /app

# Switch to non-root user early
USER node

# Copy package files and install dependencies
COPY --chown=node:node /home/ubuntu/brainpower-ai/react_renderer_next/package.json \
    /home/ubuntu/brainpower-ai/react_renderer_next/package-lock.json \
    ./

# Install all dependencies from package.json
RUN yarn install \
    --production=false \
    --frozen-lockfile \
    --network-timeout 600000 \
    --prefer-offline \
    --no-progress \
    && yarn cache clean

# Copy configuration files from react_renderer_next
COPY --chown=node:node /home/ubuntu/brainpower-ai/react_renderer_next/next.config.js \
    /home/ubuntu/brainpower-ai/react_renderer_next/tsconfig.json \
    /home/ubuntu/brainpower-ai/react_renderer_next/postcss.config.js \
    /home/ubuntu/brainpower-ai/react_renderer_next/tailwind.config.ts \
    /home/ubuntu/brainpower-ai/react_renderer_next/components.json \
    /home/ubuntu/brainpower-ai/react_renderer_next/watch-components.js \
    ./

# Copy app files from react_renderer_next
COPY --chown=node:node /home/ubuntu/brainpower-ai/react_renderer_next/src/app/page.tsx \
    /home/ubuntu/brainpower-ai/react_renderer_next/src/app/layout.tsx \
    /home/ubuntu/brainpower-ai/react_renderer_next/src/app/not-found.tsx \
    /home/ubuntu/brainpower-ai/react_renderer_next/src/app/globals.css \
    ./src/app/

# Copy utils.ts
COPY --chown=node:node /home/ubuntu/brainpower-ai/react_renderer_next/src/lib/utils.ts ./src/lib/

# Copy all shadcn UI components installed by CLI
COPY --chown=node:node /home/ubuntu/brainpower-ai/react_renderer_next/components/ui/ ./components/ui/

# Set environment variables
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=development \
    PORT=3001 \
    HOST=0.0.0.0 \
    WATCHPACK_POLLING=true \
    CHOKIDAR_USEPOLLING=true \
    NEXT_WEBPACK_POLLING=1000 \
    NEXT_HMR_POLLING_INTERVAL=1000 \
    FAST_REFRESH=true

# Create volumes for dynamic and reusable components
VOLUME [ "/app/components/dynamic", "/app/components/reusable-components" ]

EXPOSE 3001

CMD ["sh", "-c", "WATCHPACK_POLLING=true yarn dev --port 3001 & CHOKIDAR_USEPOLLING=true node watch-components.js"]