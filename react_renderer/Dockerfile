# Use a more recent Node runtime as the base image
FROM node:18.18.0

# Set the working directory in the container
WORKDIR /app

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy package.json and yarn.lock
COPY package.json yarn.lock ./

# Set yarn network timeout and concurrency
RUN yarn config set network-timeout 300000 && \
    yarn config set network-concurrency 1

# Create .env file to skip preflight check
RUN echo "SKIP_PREFLIGHT_CHECK=true" > .env

# Install dependencies
RUN yarn install

# Add html2canvas and serve
RUN yarn add html2canvas && \
    yarn global add serve \
    yarn add @babel/traverse@7.23.2 @babel/core@7.22.20 && \
    yarn add @babel/helper-remap-async-to-generator@7.22.20 && \
    export NODE_OPTIONS="--max-old-space-size=8192" && \

# Add node_modules/.bin to PATH
ENV PATH=/app/node_modules/.bin:$PATH

# Copy the entire project
COPY . .

# Expose the port the app runs on
EXPOSE 3001

# Set environment variable for create-react-app to use the correct port
ENV PORT=3001
ENV HOST=0.0.0.0
ENV NODE_ENV=development
ENV NODE_OPTIONS=--max-old-space-size=8192

# Expose port
EXPOSE 3001

# Start the app using the serve script
CMD ["yarn", "start"]