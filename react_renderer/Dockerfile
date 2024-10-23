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

 # Ensure all files and directories are owned by 'nextjs'
RUN chown -R nextjs:nextjs /app

# Copy package.json and yarn.lock
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install

# Copy Next.js configuration files
COPY next.config.js .babelrc ./

# Create a non-root user and set permissions
RUN useradd -m -s /bin/bash -u 1001 nextjs && \
    chown -R nextjs:nextjs /app

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

# Start Next.js development server
CMD ["yarn", "dev"]