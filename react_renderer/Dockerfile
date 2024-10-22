# Use Node 18.18.0 as base image
FROM node:18.18.0

# Set the working directory
WORKDIR /app

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy package files first for better caching
COPY package.json yarn.lock ./
COPY tsconfig.json webpack.config.js ./

# Configure yarn
RUN yarn config set network-timeout 600000 && \
    yarn config set network-concurrency 1

# Install specific Babel dependencies first
RUN yarn add -D \
    @babel/core@7.22.0 \
    @babel/traverse@7.23.2 \
    @babel/helper-remap-async-to-generator@7.22.20 \
    @babel/preset-env@7.22.0 \
    @babel/preset-react@7.22.0 \
    @babel/preset-typescript@7.22.0

# Install dependencies
RUN yarn install --frozen-lockfile && \
    yarn add html2canvas@1.4.1 && \
    yarn global add serve@14.2.0

# Create necessary directories
RUN mkdir -p /app/src /app/public /app/build

# Create .env file
RUN echo "SKIP_PREFLIGHT_CHECK=true\n\
DISABLE_ESLINT_PLUGIN=true\n\
GENERATE_SOURCEMAP=false\n\
BROWSER=none\n\
HOST=0.0.0.0\n\
PORT=3001" > .env

# Add node_modules/.bin to PATH
ENV PATH=/app/node_modules/.bin:$PATH

# Set environment variables
ENV PORT=3001
ENV HOST=0.0.0.0
ENV NODE_ENV=development
ENV NODE_OPTIONS="--max-old-space-size=8192"
ENV BROWSER=none
ENV WATCHPACK_POLLING=true
ENV BABEL_ENV=development

# Set proper permissions
RUN chown -R node:node /app

# Switch to non-root user
USER node

# Expose port
EXPOSE 3001

# Create startup script
RUN echo '#!/bin/sh\n\
cd /app\n\
if [ ! -f "src/component.js" ]; then\n\
  echo "// Initial component\nexport default function Component() {\n  return <div>Loading...</div>\n}" > src/component.js\n\
fi\n\
yarn start' > /app/start.sh && \
chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3001/ || exit 1

ENTRYPOINT ["/app/start.sh"]