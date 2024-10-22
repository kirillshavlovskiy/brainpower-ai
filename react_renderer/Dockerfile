# Update to Node 18 for TypeScript compatibility
FROM node:18.18.0

# Set the working directory in the container
WORKDIR /app

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy package files first
COPY package.json ./

# Remove any existing lock files and create .env
RUN rm -f package-lock.json yarn.lock && \
    echo "SKIP_PREFLIGHT_CHECK=true" > .env

# Set yarn network timeout and concurrency
RUN yarn config set network-timeout 300000 && \
    yarn config set network-concurrency 1

# Install core dependencies
RUN yarn install

# Install TypeScript and related packages
RUN yarn add -D \
    typescript@4.9.5 \
    @types/node@18.18.0 \
    @types/react@17.0.2 \
    @types/react-dom@17.0.2 \
    @typescript-eslint/parser@5.62.0 \
    @typescript-eslint/eslint-plugin@5.62.0

# Install UI dependencies
RUN yarn add \
    @mui/material@5.13.2 \
    @mui/icons-material@5.11.16 \
    @emotion/react@11.11.0 \
    @emotion/styled@11.11.0 \
    html2canvas

# Install serve globally
RUN yarn global add serve

# Add node_modules/.bin to PATH
ENV PATH=/app/node_modules/.bin:$PATH

# Create TypeScript configuration
RUN echo '{\
    "compilerOptions": {\
        "target": "es5",\
        "lib": ["dom", "dom.iterable", "esnext"],\
        "allowJs": true,\
        "skipLibCheck": true,\
        "esModuleInterop": true,\
        "allowSyntheticDefaultImports": true,\
        "strict": true,\
        "forceConsistentCasingInFileNames": true,\
        "noFallthroughCasesInSwitch": true,\
        "module": "esnext",\
        "moduleResolution": "node",\
        "resolveJsonModule": true,\
        "isolatedModules": true,\
        "noEmit": true,\
        "jsx": "react-jsx"\
    },\
    "include": ["src"]\
}' > tsconfig.json

# Create src directory
RUN mkdir -p src public

# Set environment variables
ENV PORT=3001
ENV HOST=0.0.0.0
ENV NODE_ENV=development
ENV NODE_OPTIONS=--max-old-space-size=8192
ENV WATCHPACK_POLLING=true

# Expose port
EXPOSE 3001

# Start command
CMD ["sh", "-c", "yarn install && yarn start"]