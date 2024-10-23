# Use Node.js 18.18.0 as the base image
FROM node:18.18.0-slim

# Install necessary system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    procps \
    curl \
    netcat-traditional \
    lsof \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Add Next.js specific directories
RUN mkdir -p /app/pages /app/components /app/public /app/styles

# Install global Next.js CLI
RUN npm install -g next@latest

# Create a non-root user for better security
RUN useradd -m -s /bin/bash -u 1001 nextjs && \
    chown -R nextjs:nextjs /app

# Copy configuration files first
COPY package.json yarn.lock ./
COPY tailwind.config.js postcss.config.js ./
COPY styles/globals.css ./styles/

# Install dependencies
RUN yarn install

# Switch to non-root user
USER nextjs

# Expose port 3001
EXPOSE 3001

# Set environment variables
ENV PORT=3001
ENV HOST=0.0.0.0
ENV NODE_ENV=development
ENV NODE_OPTIONS="--max-old-space-size=8192"
ENV NEXT_TELEMETRY_DISABLED=1
ENV WATCHPACK_POLLING=true

# Add healthcheck
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=3 \
    CMD nc -z localhost 3001 || exit 1

# Start the Next.js development server
CMD ["yarn", "dev"]