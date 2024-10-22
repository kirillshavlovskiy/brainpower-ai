# Use a more recent Node runtime as the base image
FROM node:18.18.0

# Set the working directory in the container
WORKDIR /app

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    procps \  # For pkill
    && rm -rf /var/lib/apt/lists/*

# Install yarn globally
RUN npm install -g yarn

# Copy package files
COPY package*.json ./

# Set yarn network timeout and concurrency
RUN yarn config set network-timeout 300000 && \
    yarn config set network-concurrency 1

# Create .env file to skip preflight check
RUN echo "SKIP_PREFLIGHT_CHECK=true" > .env

# Install dependencies
RUN yarn install

# Add node_modules/.bin to PATH
ENV PATH=/app/node_modules/.bin:$PATH

# Create necessary directories
RUN mkdir -p src public build

# Set environment variables
ENV PORT=3001
ENV HOST=0.0.0.0
ENV NODE_ENV=development
ENV NODE_OPTIONS=--max-old-space-size=8192

# Expose port
EXPOSE 3001

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD node -e "process.exit(require('http').get('http://localhost:3001', (r) => r.statusCode === 200 ? 0 : 1).on('error', () => process.exit(1)))"

# Start command wrapper script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["yarn", "start"]