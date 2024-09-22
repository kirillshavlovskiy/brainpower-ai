# Use a more recent Node runtime as the base image
FROM node:16

# Set the working directory in the container
WORKDIR /app

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
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
    yarn global add serve

# Add node_modules/.bin to PATH
ENV PATH=/app/node_modules/.bin:$PATH

# Copy the entire project
COPY . .

# Expose the port the app runs on
EXPOSE 3001

# Set environment variable for create-react-app to use the correct port
ENV PORT=3001


# Start the app using serve
CMD ["serve", "-s", "build", "-l", "3001"]