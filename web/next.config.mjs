/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The prototype reads pre-computed artefacts from public/data, so every page
  // can be statically generated and the whole site deployed as static files.
  output: process.env.IMMUNIS_STATIC === "1" ? "export" : undefined,
  images: { unoptimized: true },
};

export default nextConfig;
