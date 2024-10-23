// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  pageExtensions: ['js', 'jsx', 'ts', 'tsx'],

  transpilePackages: [
    "@mui/material",
    "@mui/icons-material",
    "@emotion/react",
    "@emotion/styled",
    "lucide-react"
  ],

  webpack: (config, { buildId, dev, isServer, defaultLoaders }) => {
    // Handle both JS and TS files
    config.module.rules.push({
      test: /\.(js|jsx|ts|tsx)$/,
      use: [defaultLoaders.babel],
      exclude: /node_modules/,
    });

    // Add watching options
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }

    return config;
  },

  experimental: {
    // Enable emotion
    emotion: true
  }
}

module.exports = nextConfig