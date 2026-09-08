/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: false,
  productionBrowserSourceMaps: false,
  experimental: {
    webpackBuildWorker: true,
  },
};

export default nextConfig;
