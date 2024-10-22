# Use Node.js 18.18.0 as the base image
FROM node:18.18.0

# Set the working directory
WORKDIR /app

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y \
  python3 \
  make \
  g++ \
  procps \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Copy package.json and yarn.lock into the container
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install

# Copy the rest of the application code
COPY . .

# Expose port 3001
EXPOSE 3001

# Set environment variables
ENV PORT=3001
ENV HOST=0.0.0.0
ENV NODE_ENV=development
ENV NODE_OPTIONS="--max-old-space-size=8192"
ENV NEXT_TELEMETRY_DISABLED=1

# Start the Next.js development server
CMD ["yarn", "dev", "-p", "3001"]