# Use slim version for smaller image size
FROM node:18-slim

WORKDIR /app

# Install only essential tools
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create only the dynamic components directory and set permissions
RUN mkdir -p /app/components/dynamic /app/src/app /app/styles && \
    chown -R 1000:1000 /app && \
    chmod -R 755 /app

# Switch to non-root user early
USER node

# Copy package files
COPY --chown=node:node package.json ./

# Install shadcn dependencies first
RUN yarn add \
    @radix-ui/react-dialog \
    @radix-ui/react-slot \
    @radix-ui/react-toast \
    @radix-ui/react-label \
    @radix-ui/react-select \
    @radix-ui/react-separator \
    @radix-ui/react-switch \
    @radix-ui/react-tabs \
    @radix-ui/react-hover-card \
    class-variance-authority \
    clsx \
    tailwind-merge \
    tailwindcss-animate \
    lucide-react

# Install other dependencies
RUN yarn install \
    --production \
    --frozen-lockfile \
    --network-timeout 600000 \
    --prefer-offline \
    --no-progress

# Pre-download SWC binaries
RUN yarn add @next/swc-linux-x64-gnu @next/swc-linux-x64-musl

# Copy exact files in exact locations
COPY --chown=node:node next.config.js ./
COPY --chown=node:node tsconfig.json ./
COPY --chown=node:node postcss.config.js ./
COPY --chown=node:node tailwind.config.ts ./
COPY --chown=node:node components.json ./
COPY --chown=node:node watch-components.js ./
COPY --chown=node:node src/app/page.tsx ./src/app/
COPY --chown=node:node src/app/layout.tsx ./src/app/
COPY --chown=node:node src/app/not-found.tsx ./src/app/
COPY --chown=node:node src/app/globals.css ./src/app/
COPY --chown=node:node styles/* ./styles/

# Set essential environment variables
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=development \
    PORT=3001 \
    HOST=0.0.0.0 \
    WATCHPACK_POLLING=true \
    CHOKIDAR_USEPOLLING=true \
    NEXT_WEBPACK_POLLING=1000 \
    NEXT_HMR_POLLING_INTERVAL=1000

# Create volume only for dynamic components
VOLUME [ "/app/components/dynamic" ]

# Expose port 3001
EXPOSE 3001

# Start both Next.js and the watch script
CMD ["sh", "-c", "WATCHPACK_POLLING=true yarn dev --port 3001 & CHOKIDAR_USEPOLLING=true node watch-components.js"]