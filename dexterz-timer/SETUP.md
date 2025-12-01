# Setup Guide

## Quick Start

Follow these steps to get the Time Tracker system running locally.

### 1. Install Dependencies

```bash
# Install all dependencies for the monorepo
npm install

# Or use pnpm for faster installation
pnpm install
```

### 2. Set Up Environment Variables

```bash
# Copy environment templates
cp .env.example .env
cp apps/backend/.env.example apps/backend/.env
cp apps/admin/.env.example apps/admin/.env
```

Edit the `.env` files with your configuration:

**Root `.env`:**
```env
POSTGRES_PASSWORD=your_secure_password
JWT_ACCESS_SECRET=your_random_access_secret
JWT_REFRESH_SECRET=your_random_refresh_secret
NEXT_PUBLIC_API_URL=http://localhost:3001/api
```

**`apps/backend/.env`:**
```env
DATABASE_URL="postgresql://timetracker:your_secure_password@localhost:5432/timetracker?schema=public"
REDIS_HOST=localhost
REDIS_PORT=6379
JWT_ACCESS_SECRET=your_random_access_secret
JWT_REFRESH_SECRET=your_random_refresh_secret
PORT=3001
NODE_ENV=development
DEFAULT_TIMEZONE=Asia/Karachi
```

**`apps/admin/.env`:**
```env
NEXT_PUBLIC_API_URL=http://localhost:3001/api
```

### 3. Start Database Services

Using Docker Compose (recommended):

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis
```

Or install locally:
- PostgreSQL 16
- Redis 7

### 4. Run Database Migrations

```bash
# Generate Prisma client
npm run prisma:generate

# Run migrations
npm run prisma:migrate
```

### 5. Start Development Servers

Open three terminal windows:

**Terminal 1 - Backend API:**
```bash
npm run dev:backend
```

**Terminal 2 - Admin Panel:**
```bash
npm run dev:admin
```

**Terminal 3 - Desktop App (optional):**
```bash
npm run dev:desktop
```

### 6. Access the Applications

- **Admin Panel:** http://localhost:3000
- **Backend API:** http://localhost:3001/api
- **Desktop App:** Electron window will open automatically

### 7. Create First User

Register through the admin panel at http://localhost:3000/login or use the API:

```bash
curl -X POST http://localhost:3001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password123",
    "fullName": "Admin User",
    "orgName": "My Organization"
  }'
```

## Development Workflow

### Running Individual Services

```bash
# Backend only
npm run dev:backend

# Admin panel only
npm run dev:admin

# Desktop app only
npm run dev:desktop
```

### Database Management

```bash
# Open Prisma Studio (database GUI)
npm run prisma:studio

# Create a new migration
cd apps/backend
npx prisma migrate dev --name migration_name

# Reset database (WARNING: deletes all data)
npx prisma migrate reset
```

### Building for Production

```bash
# Build all applications
npm run build:backend
npm run build:admin
npm run build:desktop

# Or build individually
npm run build:backend
npm run build:admin
npm run build:desktop
```

## Project Structure

```
time-tracker/
├── apps/
│   ├── backend/          # NestJS API server
│   │   ├── src/
│   │   │   ├── auth/     # Authentication module
│   │   │   ├── users/    # User management
│   │   │   ├── activity/ # Activity tracking
│   │   │   ├── reports/  # Reports and exports
│   │   │   ├── organizations/ # Org settings
│   │   │   └── worker/   # Background jobs
│   │   └── prisma/       # Database schema
│   ├── admin/            # Next.js admin panel
│   │   └── src/
│   │       ├── app/      # App router pages
│   │       └── lib/      # Utilities and API client
│   └── desktop/          # Electron desktop app
│       └── src/
│           ├── main/     # Electron main process
│           └── renderer/ # React UI
├── packages/
│   └── shared/           # Shared types and utilities
└── docker/               # Docker configurations
```

## Troubleshooting

### Port Already in Use

If you get "port already in use" errors:

```bash
# Find process using port 3001 (backend)
lsof -i :3001
kill -9 <PID>

# Find process using port 3000 (admin)
lsof -i :3000
kill -9 <PID>
```

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Test connection
psql postgresql://timetracker:password@localhost:5432/timetracker
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

### Prisma Issues

```bash
# Regenerate Prisma client
npm run prisma:generate

# Format schema
cd apps/backend
npx prisma format

# Validate schema
npx prisma validate
```

### Desktop App Issues

```bash
# Clear Electron cache
rm -rf apps/desktop/node_modules/.cache

# Rebuild native modules
cd apps/desktop
npm rebuild
```

## Next Steps

1. **Configure Time Rules:** Visit Settings in the admin panel to configure working hours, break times, and idle thresholds.

2. **Add Users:** Create user accounts for your team members.

3. **Download Desktop App:** Build and distribute the desktop app to team members.

4. **Set Up Monitoring:** Configure logging and monitoring for production use.

5. **Deploy:** Follow the DEPLOYMENT.md guide for production deployment.

## Additional Resources

- [API Documentation](./API.md) - API endpoints reference
- [Deployment Guide](./DEPLOYMENT.md) - Production deployment
- [Architecture Overview](./ARCHITECTURE.md) - System architecture

## Support

For issues and questions:
- Check existing GitHub issues
- Create a new issue with detailed information
- Contact the development team
