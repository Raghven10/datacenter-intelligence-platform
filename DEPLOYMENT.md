# Deployment Manual

This document provides detailed instructions for deploying the Daily Inspection Platform in various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Docker Deployment (Recommended)](#docker-deployment-recommended)
3. [Manual Deployment](#manual-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [Troubleshooting](#troubleshooting)
7. [Production Considerations](#production-considerations)

## Prerequisites

### For Docker Deployment
- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- 10GB disk space

### For Manual Deployment
- Python 3.13+
- PostgreSQL 15+
- Redis 7+
- 4GB RAM minimum
- 20GB disk space

## Docker Deployment (Recommended)

### 1. Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd di_app

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file and set required variables:

```bash
# CRITICAL: Set a strong secret key
SECRET_KEY=<generate-with: openssl rand -base64 32>

# Database credentials
POSTGRES_USER=di_user
POSTGRES_PASSWORD=<strong-password-here>
POSTGRES_DB=di_database

# Application settings
APP_ENV=production
DEBUG=False
```

### 3. Build and Start Services

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f app
```

### 4. Initialize Database

```bash
# Run migrations (if any)
docker-compose exec app python migrations/add_full_name.py

# Create first admin user (register via web UI)
# Navigate to http://localhost:8000/register
```

### 5. Verify Deployment

```bash
# Check application health
curl http://localhost:8000/health

# Check database connection
docker-compose exec postgres psql -U di_user -d di_database -c "SELECT 1;"

# Check Redis
docker-compose exec redis redis-cli ping
```

## Manual Deployment

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3.13 python3.13-venv postgresql-15 redis-server
```

**macOS:**
```bash
brew install python@3.13 postgresql@15 redis
brew services start postgresql@15
brew services start redis
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure PostgreSQL

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE USER di_user WITH PASSWORD 'your-secure-password';
CREATE DATABASE di_database OWNER di_user;
GRANT ALL PRIVILEGES ON DATABASE di_database TO di_user;
EOF
```

### 4. Configure Environment

```bash
# Create .env file
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 5. Run Database Migrations

```bash
# Apply migrations
python migrations/add_full_name.py
```

### 6. Start Application

```bash
# Development
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Production (with Gunicorn)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (CRITICAL) | `openssl rand -base64 32` |
| `POSTGRES_PASSWORD` | Database password | `SecurePass123!` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `POSTGRES_USER` | Database user | `di_user` |
| `POSTGRES_DB` | Database name | `di_database` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `APP_ENV` | Environment (dev/prod) | `production` |
| `DEBUG` | Debug mode | `False` |
| `PORT` | Application port | `8000` |

### Generating Secure Keys

```bash
# Generate SECRET_KEY
openssl rand -base64 32

# Or using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Database Setup

### Backup

```bash
# Docker
docker-compose exec postgres pg_dump -U di_user di_database > backup.sql

# Manual
pg_dump -U di_user di_database > backup.sql
```

### Restore

```bash
# Docker
docker-compose exec -T postgres psql -U di_user di_database < backup.sql

# Manual
psql -U di_user di_database < backup.sql
```

### Migrations

```bash
# Check current schema
docker-compose exec postgres psql -U di_user -d di_database -c "\dt"

# Run specific migration
docker-compose exec app python migrations/add_full_name.py
```

## Troubleshooting

### Application Won't Start

**Check logs:**
```bash
# Docker
docker-compose logs app

# Manual
tail -f server.log
```

**Common issues:**
- Database not running: `docker-compose up -d postgres`
- Redis not running: `docker-compose up -d redis`
- Port already in use: Change `PORT` in `.env`

### Database Connection Failed

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres psql -U di_user -d di_database

# Verify credentials in .env match docker-compose.yml
```

### Redis Connection Failed

```bash
# Verify Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping

# Should return: PONG
```

### Permission Errors

```bash
# Fix profile picture directory permissions
sudo chown -R 1000:1000 app/static/profile_pics

# Docker: Rebuild with correct permissions
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### WebSocket Notifications Not Working

1. Check Redis is running
2. Verify `REDIS_URL` in environment
3. Check browser console for WebSocket errors
4. Ensure firewall allows WebSocket connections

## Production Considerations

### Security

1. **Use HTTPS**: Deploy behind nginx/traefik with SSL
2. **Strong Secrets**: Generate unique `SECRET_KEY`
3. **Database Security**: Use strong passwords, restrict network access
4. **Firewall**: Only expose necessary ports (80, 443)
5. **Regular Updates**: Keep dependencies updated

### Performance

1. **Database Tuning**: Adjust PostgreSQL settings for your workload
2. **Redis Persistence**: Configure AOF for data durability
3. **Worker Processes**: Scale with `docker-compose scale app=4`
4. **Caching**: Enable query caching in PostgreSQL
5. **CDN**: Serve static files via CDN

### Monitoring

1. **Health Checks**: Monitor `/health` endpoint
2. **Logs**: Centralize logs (ELK stack, CloudWatch)
3. **Metrics**: Use Prometheus + Grafana
4. **Alerts**: Set up alerts for service failures
5. **Backups**: Automate daily database backups

### Scaling

**Horizontal Scaling:**
```yaml
# docker-compose.yml
services:
  app:
    deploy:
      replicas: 4
```

**Load Balancer:**
```nginx
upstream di_app {
    server app1:8000;
    server app2:8000;
    server app3:8000;
    server app4:8000;
}
```

### Backup Strategy

1. **Database**: Daily automated backups
2. **Uploads**: Sync `app/static/profile_pics` to S3/object storage
3. **Configuration**: Version control `.env` template
4. **Retention**: Keep 30 days of backups

### SSL/TLS Configuration

**Using nginx:**
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket support
    location /notifications/ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Maintenance

### Update Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d

# Run migrations if needed
docker-compose exec app python migrations/add_full_name.py
```

### Clean Up

```bash
# Remove old images
docker image prune -a

# Remove unused volumes
docker volume prune

# Clean logs
docker-compose exec app sh -c "truncate -s 0 server.log"
```

---

**For additional support, refer to README.md or contact the development team.**
