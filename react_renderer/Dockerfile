# Use Node 18 as base
FROM node:18.18.0

# Set working directory
WORKDIR /app

# Install necessary build tools
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV NODE_ENV=development
ENV PORT=3001
ENV HOST=0.0.0.0
ENV NODE_OPTIONS="--max-old-space-size=8192"

# Create .env file with necessary configurations
RUN echo "SKIP_PREFLIGHT_CHECK=true" > .env && \
    echo "DISABLE_ESLINT_PLUGIN=true" >> .env && \
    echo "TSC_COMPILE_ON_ERROR=true" >> .env

# Install global packages
RUN yarn global add \
    serve \
    typescript \
    @types/react \
    @types/react-dom

# Copy only configuration files
COPY package.json yarn.lock ./
COPY tsconfig.json ./
COPY tailwind.config.js postcss.config.js ./


# Configure yarn and install dependencies
RUN yarn config set network-timeout 300000 && \
    yarn config set network-concurrency 4 && \
    yarn install

# Create necessary directories with correct permissions
RUN mkdir -p /app/src /app/public /app/build && \
    chown -R node:node /app && \
    chmod -R 755 /app

# Add node_modules/.bin to PATH
ENV PATH=/app/node_modules/.bin:$PATH

# Expose port
EXPOSE 3001

# Switch to non-root user
USER node

# Default command
CMD ["yarn", "start"]