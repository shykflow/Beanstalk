/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@time-tracker/shared'],
  output: 'export',

}

module.exports = nextConfig
