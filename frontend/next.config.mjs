const backendHostport = process.env.BACKEND_HOSTPORT ?? "localhost:8000";
const backendBaseUrl = process.env.SERVER_API_BASE_URL ?? `http://${backendHostport}`;

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendBaseUrl}/api/:path*`
      }
    ];
  }
};

export default nextConfig;
