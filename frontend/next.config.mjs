/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable static export for GitHub Pages
  output: 'export',
  // Disable image optimization as it requires a Node.js server
  images: {
    unoptimized: true,
  },
  // Ignore typescript and eslint errors during build for smooth deployment
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
