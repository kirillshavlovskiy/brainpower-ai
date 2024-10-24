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

# Create Next.js directory structure
RUN mkdir -p /app/pages /app/components /app/public /app/styles /app/.next

# Install base Next.js dependencies
RUN yarn init -y && \
    yarn add next@latest react@latest react-dom@latest && \
    yarn add --dev babel-plugin-module-resolver @babel/core @babel/preset-react

# Copy configuration files
COPY next.config.js ./
COPY .babelrc ./
COPY package.json yarn.lock ./

# Update package.json scripts
RUN node -e "const pkg=require('./package.json'); \
    pkg.scripts=Object.assign(pkg.scripts||{}, {dev:'next dev -p 3001'}); \
    require('fs').writeFileSync('./package.json', JSON.stringify(pkg, null, 2))"

# Install remaining dependencies
RUN yarn install

# Create a non-root user and set permissions
RUN useradd -m -s /bin/bash -u 1001 nextjs && \
    chown -R nextjs:nextjs /app && \
    chmod -R 755 /app

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

# Start Next.js development server
CMD ["yarn", "dev"]