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

# Install global packages needed for any React app
RUN yarn global add \
    serve \
    typescript \
    @types/react \
    @types/react-dom

# Pre-install common dependencies that all apps might use
COPY package.json ./

# Configure yarn
RUN yarn config set network-timeout 300000 && \
    yarn config set network-concurrency 4 && \
    yarn install

# Create necessary directories with correct permissions
RUN mkdir -p /app/src && \
    mkdir -p /app/styles && \
    mkdir -p /app/public && \
    mkdir -p /app/build && \
    chown -R node:node /app

# Add node_modules/.bin to PATH
ENV PATH=/app/node_modules/.bin:$PATH

# Copy the entire project
COPY . .

# Expose port
EXPOSE 3001

# Default command that can be overridden
CMD ["yarn", "start"]