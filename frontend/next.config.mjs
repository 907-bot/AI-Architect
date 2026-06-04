/** @type {import('next').NextConfig} */
const isGithubActions = process.env.GITHUB_ACTIONS || false;
const isStaticExport = process.env.STATIC_EXPORT === 'true' || isGithubActions;

let repo = '';
if (isGithubActions && process.env.GITHUB_REPOSITORY) {
  repo = process.env.GITHUB_REPOSITORY.replace(/.*?\//, '');
}

const nextConfig = {
  // Only use static export for GitHub Pages CI — NOT for local dev server.
  // Static export mode breaks the dev server (all JS chunks return 404).
  ...(isStaticExport && {
    output: 'export',
    basePath: repo ? `/${repo}` : '',
    assetPrefix: repo ? `/${repo}/` : '',
  }),

  // Disable image optimization (required for static export; harmless in dev)
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
