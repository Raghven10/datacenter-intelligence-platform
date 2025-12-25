# Using Docker Compose with Local Services

This guide explains how to use `docker-compose.local.yml` to run only the application container while connecting to your existing local PostgreSQL and Redis services.

## Prerequisites

Ensure your local services are running:

```bash
# Check PostgreSQL
psql -U postgres -c "SELECT 1;"

# Check Redis
redis-cli ping
# Should return: PONG
```

## Configuration

The `docker-compose.local.yml` file uses `host.docker.internal` to connect to services on your host machine. This works on:
- ✅ Docker Desktop (Mac/Windows)
- ✅ Docker on Linux (with `extra_hosts` configuration)

## Usage

### Start the application

```bash
docker-compose -f docker-compose.local.yml up -d
```

### View logs

```bash
docker-compose -f docker-compose.local.yml logs -f app
```

### Stop the application

```bash
docker-compose -f docker-compose.local.yml down
```

### Rebuild after code changes

```bash
docker-compose -f docker-compose.local.yml up -d --build
```

## Environment Variables

Make sure your `.env` file has the correct credentials for your local services:

```bash
# Database (your local PostgreSQL)
POSTGRES_HOST=host.docker.internal  # Automatically set in docker-compose.local.yml
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-local-password
POSTGRES_DB=datacenter_db

# Redis (your local Redis)
REDIS_URL=redis://host.docker.internal:6379/0  # Automatically set

# Security
SECRET_KEY=your-secret-key
```

## Troubleshooting

### Cannot connect to PostgreSQL

1. **Check PostgreSQL is listening on all interfaces**:
   ```bash
   # Edit postgresql.conf
   listen_addresses = '*'
   ```

2. **Check pg_hba.conf allows connections**:
   ```
   host    all             all             172.17.0.0/16           md5
   ```

3. **Restart PostgreSQL**:
   ```bash
   brew services restart postgresql@15  # macOS
   sudo systemctl restart postgresql    # Linux
   ```

### Cannot connect to Redis

1. **Check Redis is listening on all interfaces**:
   ```bash
   # Edit redis.conf
   bind 0.0.0.0
   ```

2. **Restart Redis**:
   ```bash
   brew services restart redis  # macOS
   sudo systemctl restart redis # Linux
   ```

### Port conflicts

If port 8000 is already in use, change it in `.env`:
```bash
PORT=8080
```

Then restart:
```bash
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d
```

## Comparison: Full Stack vs Local Services

| Feature | `docker-compose.yml` | `docker-compose.local.yml` |
|---------|---------------------|---------------------------|
| PostgreSQL | ✅ New container | ❌ Use existing local |
| Redis | ✅ New container | ❌ Use existing local |
| Application | ✅ Container | ✅ Container |
| Data persistence | Docker volumes | Local filesystem |
| Port conflicts | Possible (5432, 6379) | None |
| Best for | Production/Testing | Development |
