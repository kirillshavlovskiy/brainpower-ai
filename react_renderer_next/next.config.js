/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
  assetPrefix: process.env.NODE_ENV === 'production'
    ? `https://${process.env.PORT}.brainpower-ai.net`
    : '',

  // Public runtime configuration
  publicRuntimeConfig: {
    basePath: process.env.NODE_ENV === 'production'
      ? `https://${process.env.PORT}.brainpower-ai.net`
      : '',
  },

  // Static file serving
  images: {
    domains: ['brainpower-ai.net'],
    loader: 'default',
    path: `https://${process.env.PORT}.brainpower-ai.net/_next/image`
  },
  compiler: {
    // Enable emotion
    emotion: true
  }
}

module.exports = nextConfig