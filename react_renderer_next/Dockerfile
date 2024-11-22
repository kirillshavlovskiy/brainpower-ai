# Use slim version for smaller image size
FROM node:18-slim

WORKDIR /app

# Install only essential tools
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package.json ./

# Install shadcn dependencies first
RUN yarn add @radix-ui/react-dialog \
    @radix-ui/react-slot \
    @radix-ui/react-toast \
    class-variance-authority \
    clsx \
    tailwind-merge \
    tailwindcss-animate

# Install other dependencies
RUN yarn install \
    --production \
    --frozen-lockfile \
    --network-timeout 600000 \
    --ignore-optional \
    --ignore-platform \
    --no-progress

# Pre-download SWC binaries to avoid runtime downloads
RUN yarn add @next/swc-linux-x64-gnu @next/swc-linux-x64-musl

# Create necessary directories
RUN mkdir -p \
    /app/components/dynamic \
    /app/components/ui \
    /app/src/app \
    /app/src/lib \
    /app/styles

# Copy configuration files
COPY components.json ./
COPY tailwind.config.ts ./
COPY postcss.config.js ./
COPY watch-components.js ./
COPY next.config.js ./
COPY tsconfig.json ./

# Create essential Next.js files
RUN echo '"use client";\nimport React from "react";\nimport "./globals.css";\n\nexport default function RootLayout({ children }) {\n  return (\n    <html lang="en">\n      <head>\n        <meta charSet="utf-8" />\n        <meta name="viewport" content="width=device-width, initial-scale=1" />\n      </head>\n      <body suppressHydrationWarning={true}>\n        <div id="dynamic-component-root">\n          {children}\n        </div>\n      </body>\n    </html>\n  );\n}' > /app/src/app/layout.tsx

RUN echo '"use client";\nimport dynamic from "next/dynamic";\n\nconst DynamicComponent = dynamic(() => import("/app/components/dynamic/placeholder"), {\n  ssr: false,\n  loading: () => <div>Loading...</div>\n});\n\nexport default function Home() {\n  return (\n    <main className="flex min-h-screen flex-col items-center justify-between p-24">\n      <div className="w-full max-w-5xl">\n        <DynamicComponent />\n      </div>\n    </main>\n  );\n}' > /app/src/app/page.tsx

# Copy source directories
COPY src ./src
COPY components ./components
COPY styles ./styles
COPY lib ./lib

# Set proper permissions
RUN chown -R node:node /app && \
    chmod -R 755 /app

# Create volumes for dynamic content
VOLUME /app/components/dynamic
VOLUME /app/components/ui
VOLUME /app/src

# Expose port 3001
EXPOSE 3001

# Switch to non-root user
USER node

# Set essential environment variables
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=development
ENV PORT=3001
ENV HOST=0.0.0.0
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true

# Start both Next.js and the watch script
CMD ["sh", "-c", "yarn dev & node watch-components.js"]