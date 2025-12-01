# Deployment Guide

## Prerequisites

- Ubuntu 22.04 LTS server (EC2 or similar)
- Docker and Docker Compose installed
- Domain name (optional, for production)
- SSL certificate (optional, for HTTPS)

## Initial Setup

### 1. Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Clone Repository

```bash
git clone <your-repo-url>
cd time-tracker
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with secure values
nano .env
```

**Important**: Change all default passwords and secrets!

```env
POSTGRES_PASSWORD=<strong-random-password>
JWT_ACCESS_SECRET=<random-secret-key>
JWT_REFRESH_SECRET=<random-secret-key>
NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api
```

### 4. Start Services

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Run database migrations
docker-compose exec backend npx prisma migrate deploy
```

## Database Setup

### Initial Migration

```bash
# Generate Prisma client
docker-compose exec backend npx prisma generate

# Run migrations
docker-compose exec backend npx prisma migrate deploy

# (Optional) Seed database
docker-compose exec backend npx prisma db seed
```

### Backup Database

```bash
# Create backup
docker-compose exec postgres pg_dump -U timetracker timetracker > backup_$(date +%Y%m%d).sql

# Restore backup
docker-compose exec -T postgres psql -U timetracker timetracker < backup.sql
```

## Production Deployment

### Using Nginx as Reverse Proxy

```nginx
# /etc/nginx/sites-available/timetracker

# API Backend
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Admin Panel
server {
    listen 80;
    server_name admin.yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable sites:
```bash
sudo ln -s /etc/nginx/sites-available/timetracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificates
sudo certbot --nginx -d api.yourdomain.com -d admin.yourdomain.com

# Auto-renewal is configured automatically
```

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f admin
docker-compose logs -f postgres
```

### Health Checks

```bash
# Check service status
docker-compose ps

# Check backend health
curl http://localhost:3001/api/health

# Check database connection
docker-compose exec postgres pg_isready -U timetracker
```

## Scaling

### Horizontal Scaling

For high availability, you can run multiple backend instances:

```yaml
# docker-compose.yml
services:
  backend:
    # ... existing config
    deploy:
      replicas: 3
```

### Database Optimization

PgBouncer is already configured for connection pooling. Adjust pool size in `docker-compose.yml`:

```yaml
pgbouncer:
  environment:
    DEFAULT_POOL_SIZE: 50  # Increase for more connections
    MAX_CLIENT_CONN: 2000
```

## Maintenance

### Update Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Run migrations if needed
docker-compose exec backend npx prisma migrate deploy
```

### Cleanup

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes (careful!)
docker volume prune
```

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Verify database connection
docker-compose exec backend npx prisma db pull
```

### Database connection issues

```bash
# Check PostgreSQL
docker-compose exec postgres psql -U timetracker -d timetracker -c "SELECT 1"

# Check PgBouncer
docker-compose logs pgbouncer
```

### Redis issues

```bash
# Check Redis
docker-compose exec redis redis-cli ping

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL
```

## Security Checklist

- [ ] Changed all default passwords
- [ ] Generated strong JWT secrets
- [ ] Configured firewall (UFW)
- [ ] Enabled SSL/TLS
- [ ] Set up automated backups
- [ ] Configured log rotation
- [ ] Restricted database access
- [ ] Enabled Docker security scanning
- [ ] Set up monitoring and alerts

## Desktop App Distribution

### Building Desktop Apps

```bash
cd apps/desktop

# Build for current platform
npm run package

# Build for all platforms (requires platform-specific tools)
npm run package -- --mac --win --linux
```

Distributable files will be in `apps/desktop/release/`.

### Auto-update Server

Configure electron-updater to point to your release server or GitHub Releases.

## Support

For issues and questions, refer to the main README.md or create an issue in the repository.
