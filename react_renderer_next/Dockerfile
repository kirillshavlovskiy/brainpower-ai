# Use alpine for smaller image size
FROM node:18-alpine

WORKDIR /app

# Install minimal dependencies in a single layer
RUN apk add --no-cache python3 make g++ \
    && yarn config set cache-folder /tmp/yarn-cache

# Copy only necessary files
COPY package.json ./

# Install deps with cleanup in same layer
RUN yarn install \
    --production \
    --frozen-lockfile \
    --prefer-offline \
    && yarn cache clean \
    && rm -rf /tmp/yarn-cache

# Create minimal directory structure
RUN mkdir -p \
    /app/components/dynamic \
    /app/src/app

# Copy only essential files
COPY src/app/globals.css ./src/app/
COPY src/app/layout.tsx ./src/app/
COPY src/app/page.tsx ./src/app/
COPY next.config.js tailwind.config.ts postcss.config.js ./

# Set permissions
RUN chown -R node:node /app && \
    chmod -R 755 /app

# Use bind mounts instead of volumes
EXPOSE 3001
USER node

# Minimal env vars
ENV NODE_ENV=development \
    PORT=3001 \
    HOST=0.0.0.0 \
    NODE_OPTIONS="--max-old-space-size=512"

CMD ["yarn", "dev"]