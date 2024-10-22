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

# Pre-install specific Babel dependencies
RUN yarn add -D \
    @babel/core@7.22.20 \
    @babel/traverse@7.23.2 \
    @babel/helper-remap-async-to-generator@7.22.20 \
    @babel/preset-env@7.22.20 \
    @babel/preset-react@7.22.15

# Install Next.js and related dependencies
RUN yarn add \
    next@13.5.4 \
    react@18.2.0 \
    react-dom@18.2.0 \
    @emotion/react@11.11.0 \
    @emotion/styled@11.11.0 \
    @mui/icons-material@5.11.16 \
    @mui/material@5.13.2 \
    lucide-react@0.268.0 \
    react-icons@4.2.0 \
    html2canvas@1.4.1

# Create base project structure
RUN mkdir -p /app/src/app \
    /app/public \
    /app/src/components \
    /app/src/styles \
    /app/.next

# Create Next.js config
RUN echo 'module.exports = {' > next.config.js && \
    echo '  reactStrictMode: true,' >> next.config.js && \
    echo '  swcMinify: true,' >> next.config.js && \
    echo '  experimental: {' >> next.config.js && \
    echo '    appDir: true' >> next.config.js && \
    echo '  },' >> next.config.js && \
    echo '  webpack: (config) => {' >> next.config.js && \
    echo '    config.resolve.fallback = { fs: false };' >> next.config.js && \
    echo '    return config;' >> next.config.js && \
    echo '  }' >> next.config.js && \
    echo '};' >> next.config.js

# Create base layout and page files
RUN echo 'export default function RootLayout({ children }) {\n\
  return (\n\
    <html lang="en">\n\
      <body>{children}</body>\n\
    </html>\n\
  )\n\
}' > /app/src/app/layout.jsx

RUN echo 'export default function Page() {\n\
  return <div>Loading component...</div>\n\
}' > /app/src/app/page.jsx

# Create empty component file
RUN echo 'export default function Component() {\n\
  return <div>Initial component</div>\n\
}' > /app/src/component.jsx

# Set environment variables
ENV PORT=3001
ENV HOST=0.0.0.0
ENV NODE_ENV=development
ENV NODE_OPTIONS="--max-old-space-size=8192"
ENV WATCHPACK_POLLING=true
ENV NEXT_TELEMETRY_DISABLED=1

# Set proper permissions
RUN chown -R node:node /app

# Expose port
EXPOSE 3001

# Switch to non-root user
USER node

# Create startup script that handles both initial setup and running
RUN echo '#!/bin/sh\n\
cd /app\n\
\n\
# Install dependencies if node_modules doesnt exist\n\
if [ ! -d "node_modules" ]; then\n\
    yarn install\n\
fi\n\
\n\
# Add required Babel dependencies\n\
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