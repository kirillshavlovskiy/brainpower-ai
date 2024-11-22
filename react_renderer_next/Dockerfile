# Use slim version for smaller image size
FROM node:18-slim

WORKDIR /app

# Install only essential tools
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package.json ./

# Install shadcn dependencies first
RUN yarn add @radix-ui/react-dialog \
    @radix-ui/react-slot \
    @radix-ui/react-toast \
    class-variance-authority \
    clsx \
    tailwind-merge \
    tailwindcss-animate

# Install other dependencies
RUN yarn install \
    --production \
    --frozen-lockfile \
    --network-timeout 600000 \
    --ignore-optional \
    --ignore-platform \
    --no-progress

# Pre-download SWC binaries to avoid runtime downloads
RUN yarn add @next/swc-linux-x64-gnu @next/swc-linux-x64-musl

# Create necessary directories
RUN mkdir -p \
    /app/components/dynamic \
    /app/components/ui \
    /app/src/app \
    /app/src/lib \
    /app/styles

# Copy configuration files
COPY components.json ./
COPY tailwind.config.ts ./
COPY postcss.config.js ./
COPY watch-components.js ./
COPY next.config.js ./
COPY tsconfig.json ./

# Copy source files and directories
COPY src/app/globals.css ./src/app/
COPY src/app/layout.tsx ./src/app/
COPY src/app/page.tsx ./src/app/
COPY components ./components
COPY styles ./styles
COPY lib ./lib

# Set proper permissions
RUN chown -R node:node /app && \
    chmod -R 755 /app

# Set essential environment variables
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=development
ENV PORT=3001
ENV HOST=0.0.0.0
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true
ENV NEXT_WEBPACK_POLLING=1000
ENV NEXT_HMR_POLLING_INTERVAL=1000

# Create volumes with proper permissions for file watching
VOLUME [ "/app/components/dynamic", "/app/components/ui", "/app/src" ]


# Expose port 3001
EXPOSE 3001

# Switch to non-root user
USER node

# Start both Next.js and the watch script with proper polling
CMD ["sh", "-c", "WATCHPACK_POLLING=true yarn dev --port 3001 & CHOKIDAR_USEPOLLING=true node watch-components.js"]