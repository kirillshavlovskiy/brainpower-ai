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

# Pre-download SWC binaries
RUN yarn add @next/swc-linux-x64-gnu @next/swc-linux-x64-musl

# Create only the dynamic components directory
RUN mkdir -p /app/components/dynamic

# Copy exact files in exact locations
COPY next.config.js ./
COPY tsconfig.json ./
COPY postcss.config.js ./
COPY tailwind.config.ts ./
COPY components.json ./
COPY watch-components.js ./
COPY src/app/page.tsx ./src/app/
COPY src/app/layout.tsx ./src/app/
COPY src/app/not-found.tsx ./src/app/
COPY src/app/globals.css ./src/app/

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

# Create volume only for dynamic components
VOLUME [ "/app/components/dynamic" ]

# Expose port 3001
EXPOSE 3001

# Switch to non-root user
USER node

# Start both Next.js and the watch script
CMD ["sh", "-c", "WATCHPACK_POLLING=true yarn dev --port 3001 & CHOKIDAR_USEPOLLING=true node watch-components.js"]