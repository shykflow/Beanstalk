#!/bin/bash

echo "🚀 Starting Time Tracker System..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Start database services
echo "📦 Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if Prisma client is generated
if [ ! -d "apps/backend/node_modules/.prisma" ]; then
    echo "🔧 Generating Prisma client..."
    cd apps/backend && npx prisma generate && cd ../..
fi

# Run migrations
echo "🗄️  Running database migrations..."
cd apps/backend && npx prisma migrate deploy && cd ../..

echo ""
echo "✅ Setup complete!"
echo ""
echo "Now run these commands in separate terminals:"
echo ""
echo "Terminal 1 (Backend):"
echo "  npm run dev:backend"
echo ""
echo "Terminal 2 (Admin Panel):"
echo "  npm run dev:admin"
echo ""
echo "Terminal 3 (Desktop App - Optional):"
echo "  npm run dev:desktop"
echo ""
echo "Access the applications at:"
echo "  Admin Panel: http://localhost:3000"
echo "  Backend API: http://localhost:3001/api"
echo ""
