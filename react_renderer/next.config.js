// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Disable server-side rendering for dynamic components
  experimental: {
    // Enable if needed
    // esmExternals: false,
  },
  // Configure webpack if needed
  webpack: (config, { isServer }) => {
    // Add any custom webpack config
    return config;
  },
  // Configure the dev server
  webpackDevMiddleware: config => {
    // Solve potential hot reload issues
    config.watchOptions = {
      poll: 1000,
      aggregateTimeout: 300,
    }
    return config
  },
  // Enable proper port binding
  experimental: {
    allowMiddlewareResponseBody: true,
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,OPTIONS,PATCH,DELETE,POST,PUT' },
          { key: 'Access-Control-Allow-Headers', value: '*' },
        ],
      },
    ]
  }
}

module.exports = nextConfig