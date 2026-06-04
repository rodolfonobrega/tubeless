/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.NEXT_DIST_DIR || '.next-dev',
  compress: false,
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/ws/projects/:project_id',
        destination: `${backendUrl}/ws/projects/:project_id`,
      },
    ]
  },
}

module.exports = nextConfig
