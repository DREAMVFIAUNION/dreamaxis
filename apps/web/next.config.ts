import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@dreamaxis/client", "@dreamaxis/ui"],
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
