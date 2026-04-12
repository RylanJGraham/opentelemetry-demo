/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:5100/api/:path*'
      },
      {
        source: '/ws/:path*',
        destination: 'http://127.0.0.1:5100/ws/:path*'
      }
    ];
  }
};

export default nextConfig;
