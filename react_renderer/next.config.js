// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,

  // Enable both JS and TS file handling
  pageExtensions: ['js', 'jsx', 'ts', 'tsx'],

  transpilePackages: [
    "@mui/material",
    "@mui/icons-material",
    "@emotion/react",
    "@emotion/styled",
    "lucide-react"
  ],

  // Configure webpack for mixed JS/TS
  webpack: (config, { buildId, dev, isServer, defaultLoaders }) => {
    // Ensure both JS and TS files are handled
    config.module.rules.push({
      test: /\.(js|jsx|ts|tsx)$/,
      use: [defaultLoaders.babel],
      exclude: /node_modules/,
    });

    return config;
  },

  // Development server configuration
  webpackDevMiddleware: config => {
    config.watchOptions = {
      poll: 1000,
      aggregateTimeout: 300,
    }
    return config
  }
}

module.exports = nextConfig