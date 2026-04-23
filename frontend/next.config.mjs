/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "export",   // static export → S3 + CloudFront
  trailingSlash: true,
};

export default nextConfig;
