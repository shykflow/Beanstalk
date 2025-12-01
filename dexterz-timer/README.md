# Time Tracker System

A comprehensive Hubstaff-style time tracking system with desktop app, admin panel, and backend API.

## Architecture

- **Backend API**: NestJS + Prisma + PostgreSQL
- **Admin Panel**: Next.js 14 (App Router) + Tailwind + shadcn/ui
- **Desktop App**: Electron + React + TypeScript
- **Worker**: BullMQ + Redis for background jobs
- **Database**: PostgreSQL 16 with PgBouncer

## Features

- ✅ Cross-platform desktop time tracker
- ✅ Activity monitoring (mouse/keyboard)
- ✅ Idle detection (≥5 minutes)
- ✅ Strict working hours (16:50-02:00 Asia/Karachi)
- ✅ Automatic break enforcement (22:00-23:00)
- ✅ Rich reporting and timesheets
- ✅ Role-based access control
- ✅ Manual adjustments with audit trail

## Project Structure

```
.
├── apps/
│   ├── backend/          # NestJS API
│   ├── admin/            # Next.js Admin Panel
│   └── desktop/          # Electron Desktop App
├── packages/
│   ├── shared/           # Shared types and utilities
│   └── ui/               # Shared UI components
└── docker/               # Docker configurations
```

## Getting Started

### Prerequisites

- Node.js 20+
- PostgreSQL 16
- Redis 7+
- pnpm (recommended) or npm

### Installation

```bash
# Install dependencies
npm install

# Set up environment variables
cp apps/backend/.env.example apps/backend/.env
cp apps/admin/.env.example apps/admin/.env

# Run database migrations
npm run prisma:migrate

# Generate Prisma client
npm run prisma:generate
```

### Development

```bash
# Start backend API
npm run dev:backend

# Start admin panel
npm run dev:admin

# Start desktop app
npm run dev:desktop
```

### Production Build

```bash
# Build all apps
npm run build:backend
npm run build:admin
npm run build:desktop
```

## Time Rules (Asia/Karachi)

- **Check-in window**: 16:50 → 02:00 (next day)
- **Break time**: 22:00 → 23:00 (enforced, no logging)
- **Idle threshold**: 5 minutes of no activity
- **Timezone**: Asia/Karachi (no DST currently)

## License

MIT
