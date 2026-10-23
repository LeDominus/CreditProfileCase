import type { NextConfig } from 'next'

// API proxy: the browser only ever talks to same-origin /api/*; the Next
// server forwards it to the backend. Dev default is the local backend.
// NB: rewrites are baked into dist/routes-manifest.json at BUILD time,
// so BACKEND_URL must be set as a build ARG in the Docker image.
const backendUrl = process.env.BACKEND_URL ?? 'http://127.0.0.1:5555'

const nextConfig: NextConfig = {
  reactCompiler: true,
  // Docker parity with the reference project: build output goes to ./dist.
  distDir: 'dist',
  rewrites() {
    return [{ source: '/api/:path*', destination: `${backendUrl}/api/:path*` }]
  },
}

export default nextConfig
