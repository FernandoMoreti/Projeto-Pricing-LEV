import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    API_URL_QUEUE: process.env.API_URL_QUEUE
  }
};

export default nextConfig;
