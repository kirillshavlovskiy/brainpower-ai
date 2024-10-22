/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  compiler: {
    // Enable styled-components
    styledComponents: true,
  },
  // Enable hot reloading for dynamic imports
  webpack: (config, { isServer }) => {
    // Custom webpack config if needed
    return config;
  },
}

module.exports = nextConfig;