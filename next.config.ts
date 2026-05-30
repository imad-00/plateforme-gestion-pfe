import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  // Produces a self-contained ./.next/standalone directory that the Docker
  // runner stage copies in. Cuts the final image size dramatically vs shipping
  // node_modules.
  output: "standalone",
};

export default nextConfig;
