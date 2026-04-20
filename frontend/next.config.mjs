/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    // We'll need to proxy or use CORS for the backend
    async rewrites() {
        return [
            {
                source: '/api/chat',
                destination: 'http://localhost:8000/chat',
            },
        ];
    },
};

export default nextConfig;
