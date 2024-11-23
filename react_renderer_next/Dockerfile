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
    --ignore-optional \
    --ignore-platform \
    --no-progress

# Pre-download SWC binaries
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
COPY next.config.js ./
COPY tsconfig.json ./

# Explicitly copy CSS files
COPY src/app/globals.css ./src/app/
COPY styles/* ./styles/

# Copy source files
COPY src ./src
COPY components ./components
COPY lib ./lib

# Verify globals.css exists
RUN ls -la /app/src/app/globals.css || echo "globals.css not found"

# Set proper permissions
RUN chown -R node:node /app && \
    chmod -R 755 /app

# Create volume for dynamic content
VOLUME /app/components/dynamic

# Expose port 3001
EXPOSE 3001

# Switch to non-root user
USER node

# Set essential environment variables
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=development
ENV PORT=3001
ENV HOST=0.0.0.0

# Start development server
CMD ["yarn", "dev"]