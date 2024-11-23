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

# Create minimal directory structure
RUN mkdir -p /app/components/dynamic /app/src/app && \
    chown -R 1000:1000 /app && \
    chmod -R 755 /app

# Switch to non-root user early
USER node

# Copy package files and install dependencies in one layer
COPY --chown=node:node package.json ./
RUN yarn install \
    --production \
    --frozen-lockfile \
    --network-timeout 600000 \
    --prefer-offline \
    --no-progress \
    && yarn add \
    @radix-ui/react-dialog \
    @radix-ui/react-slot \
    @radix-ui/react-toast \
    class-variance-authority \
    clsx \
    tailwind-merge \
    tailwindcss-animate \
    && yarn add @next/swc-linux-x64-gnu @next/swc-linux-x64-musl \
    && yarn cache clean \
    && rm -rf /app/.yarn-cache

# Copy exact files in exact locations
COPY --chown=node:node next.config.js \
    tsconfig.json \
    postcss.config.js \
    tailwind.config.ts \
    components.json \
    watch-components.js \
    ./

# Copy app files
COPY --chown=node:node src/app/page.tsx \
    src/app/layout.tsx \
    src/app/not-found.tsx \
    src/app/globals.css \
    ./src/app/

# Set essential environment variables
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=development \
    PORT=3001 \
    HOST=0.0.0.0 \
    WATCHPACK_POLLING=true \
    CHOKIDAR_USEPOLLING=true \
    NEXT_WEBPACK_POLLING=1000 \
    NEXT_HMR_POLLING_INTERVAL=1000 \
    FAST_REFRESH=true

# Create volume only for dynamic components
VOLUME [ "/app/components/dynamic" ]

# Expose port 3001
EXPOSE 3001

# Start both Next.js and the watch script
CMD ["sh", "-c", "WATCHPACK_POLLING=true yarn dev --port 3001 & CHOKIDAR_USEPOLLING=true node watch-components.js"]