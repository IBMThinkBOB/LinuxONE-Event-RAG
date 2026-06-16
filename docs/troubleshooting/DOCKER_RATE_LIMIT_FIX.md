# Docker Hub Rate Limit - Solutions

## Problem
You're seeing this error:
```
Error response from daemon: error from registry: You have reached your unauthenticated pull rate limit.
```

This happens because Docker Hub limits unauthenticated pulls to 100 per 6 hours per IP address.

## Solution Options

### Option 1: Install PostgreSQL Locally (Recommended for macOS)

Run the provided script:
```bash
./install_postgres_local.sh
```

This will:
- Install PostgreSQL 15 via Homebrew
- Install pgvector extension
- Create the database and user
- Initialize the schema

**Pros:**
- No Docker needed
- No rate limits
- Faster startup
- Native performance

**Cons:**
- Requires Homebrew
- Installs PostgreSQL globally

---

### Option 2: Login to Docker Hub

If you have a Docker Hub account:

```bash
docker login
# Enter your username and password
```

Then retry:
```bash
docker-compose up -d postgres
```

**Pros:**
- Simple if you have an account
- 200 pulls per 6 hours (authenticated)

**Cons:**
- Requires Docker Hub account
- Still has limits

---

### Option 3: Wait and Retry

Docker Hub rate limits reset after 6 hours. You can:

1. Wait 6 hours
2. Try again with Docker Compose

**Pros:**
- No changes needed

**Cons:**
- Have to wait

---

### Option 4: Use a Different Registry

Pull from GitHub Container Registry instead:

```bash
# Pull the image manually
docker pull ghcr.io/pgvector/pgvector:pg15

# Tag it for local use
docker tag ghcr.io/pgvector/pgvector:pg15 ankane/pgvector:latest

# Now run docker-compose
docker-compose up -d postgres
```

---

## Recommended Approach

**For macOS users:** Use Option 1 (local PostgreSQL installation)

```bash
./install_postgres_local.sh
```

**For Docker users with accounts:** Use Option 2 (login to Docker Hub)

```bash
docker login
docker-compose up -d postgres
```

## After PostgreSQL is Running

Continue with the setup:

```bash
# Activate virtual environment
source venv/bin/activate

# Ingest documents
python backend/scripts/ingest_documents.py --input data/redbooks

# Start backend
cd backend && python -m app.main
```

## Verify PostgreSQL is Working

```bash
# Test connection
psql -U raguser -d linuxone_rag -c "SELECT version();"

# Check pgvector extension
psql -U raguser -d linuxone_rag -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

## Troubleshooting

### PostgreSQL not starting (Homebrew)
```bash
brew services restart postgresql@15
```

### Connection refused
```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# Check logs
tail -f /opt/homebrew/var/log/postgresql@15.log
```

### Permission denied
```bash
# Reset permissions
psql postgres -c "ALTER USER raguser WITH PASSWORD 'ragpassword';"
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE linuxone_rag TO raguser;"
```

## Need Help?

If you're still having issues:
1. Check PostgreSQL is running: `brew services list`
2. Check the connection string in `.env` matches your setup
3. Try connecting manually: `psql -U raguser -d linuxone_rag`