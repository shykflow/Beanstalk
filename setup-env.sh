#!/bin/bash

echo "Setting up environment files..."

# Update backend .env with correct database URL
cat > apps/backend/.env << 'EOF'
# Database
DATABASE_URL="postgresql://timetracker:changeme@localhost:5432/timetracker?schema=public"

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# JWT
JWT_ACCESS_SECRET=your-access-secret-change-this-in-production
JWT_REFRESH_SECRET=your-refresh-secret-change-this-in-production
JWT_ACCESS_EXPIRATION=15m
JWT_REFRESH_EXPIRATION=30d

# Server
PORT=3001
NODE_ENV=development

# Timezone
DEFAULT_TIMEZONE=Asia/Karachi
EOF

echo "✅ Backend .env file updated"
echo "✅ Setup complete!"
