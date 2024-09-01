# Build stage
FROM node:16 AS build
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install
COPY . .
RUN yarn build

# Production stage
FROM node:16-slim
WORKDIR /app
COPY --from=build /app/build ./build
RUN yarn global add serve
EXPOSE 3001
CMD ["serve", "-s", "build", "-l", "3001"]