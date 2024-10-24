# Use Node 18 as base
FROM node:18.18.0

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
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true

# Install global packages
RUN yarn global add \
    create-react-app \
    typescript \
    serve

# Create initialization and entrypoint script
RUN echo '#!/bin/bash\n\
\n\
init_cra() {\n\
    if [ ! -f "package.json" ]; then\n\
        echo "Initializing new CRA project with TypeScript..."\n\
        create-react-app . --template typescript\n\
        # Install additional dependencies\n\
        yarn add \
            @emotion/react@^11.11.0 \
            @emotion/styled@^11.11.0 \
            @mui/icons-material@^5.11.16 \
            @mui/material@^5.13.2 \
            lucide-react@^0.268.0 \
            react-icons@^4.2.0 \
            tailwindcss@^3.3.0 \
            @tailwindcss/forms@^0.5.6 \
            @tailwindcss/typography@^0.5.10 \
            @tailwindcss/aspect-ratio@^0.4.2 \
            clsx@^2.0.0 \
            html2canvas@^1.4.1 \
            tailwind-merge@^1.14.0\n\
        # Initialize Tailwind CSS\n\
        npx tailwindcss init -p\n\
        # Configure Tailwind\n\
        echo '\''module.exports = {\n\
          content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],\n\
          darkMode: "class",\n\
          theme: { extend: {} },\n\
          plugins: [\n\
            require("@tailwindcss/forms"),\n\
            require("@tailwindcss/typography"),\n\
            require("@tailwindcss/aspect-ratio")\n\
          ]\n\
        }'\'' > tailwind.config.js\n\
        # Update index.css\n\
        echo "@tailwind base;\n@tailwind components;\n@tailwind utilities;" > src/index.css\n\
        # Set permissions\n\
        chown -R node:node /app\n\
    else\n\
        echo "Project already exists, installing dependencies..."\n\
        yarn install\n\
    fi\n\
}\n\
\n\
init_cra\n\
exec "$@"' > /app/docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/components && \
    mkdir -p /app/styles && \
    chown -R node:node /app

# Expose port
EXPOSE 3001

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["yarn", "start"]