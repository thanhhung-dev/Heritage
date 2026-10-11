/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/tour-assets/tuduc.glb",
        destination: "https://pub-2fc54e5237344dc9b845f2ff2c9309f8.r2.dev/TuDuc/TuDuckt.glb",
      },
    ];
  },
};

module.exports = nextConfig;
