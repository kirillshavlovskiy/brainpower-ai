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

# Install create-next-app globally
RUN yarn global add create-next-app@latest

# Pre-install core dependencies to speed up project creation
RUN yarn add -D \
    @babel/core@7.22.20 \
    @babel/traverse@7.23.2 \
    @babel/helper-remap-async-to-generator@7.22.20 \
    @babel/preset-env@7.22.20 \
    @babel/preset-react@7.22.15

# Install UI dependencies that will be needed
RUN yarn add \
    @emotion/react@11.11.0 \
    @emotion/styled@11.11.0 \
    @mui/icons-material@5.11.16 \
    @mui/material@5.13.2 \
    lucide-react@0.268.0 \
    react-icons@4.2.0 \
    html2canvas@1.4.1

# Create necessary directories
RUN mkdir -p /app/src \
    /app/public \
    /app/build \
    /app/.next

# Set environment variables
ENV PORT=3001
ENV HOST=0.0.0.0
ENV NODE_ENV=development
ENV NODE_OPTIONS="--max-old-space-size=8192"
ENV WATCHPACK_POLLING=true
ENV NEXT_TELEMETRY_DISABLED=1

# Create empty package.json for volume mounting
RUN echo '{\n\
  "name": "react_renderer",\n\
  "version": "1.0.0",\n\
  "private": true\n\
}' > /app/package.json

# Set proper permissions
RUN chown -R node:node /app

# Expose port
EXPOSE 3001

# Switch to non-root user
USER node

# Create startup script that matches your container creation logic
RUN echo '#!/bin/sh\n\
cd /app\n\
\n\
# Check if we need to create a new Next.js project\n\
if [ ! -f "next.config.js" ]; then\n\
    if [ -n "$APP_NAME" ]; then\n\
        echo "Creating new Next.js project: $APP_NAME"\n\
        yarn create next-app $APP_NAME --typescript --eslint --tailwind --src-dir --app --import-alias "@/*" && \
        mv $APP_NAME/* . && \
        rm -rf $APP_NAME\n\
    fi\n\
fi\n\
\n\
# Install/update Babel dependencies\n\
yarn add @babel/traverse@7.23.2 @babel/core@7.22.20 @babel/helper-remap-async-to-generator@7.22.20\n\
\n\
# Start development server\n\
yarn dev -p 3001' > /app/start.sh && \
    chmod +x /app/start.sh

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3001/ || exit 1

# Set the entrypoint
ENTRYPOINT ["/app/start.sh"]