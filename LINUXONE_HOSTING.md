# LinuxONE Production Hosting Guide

Complete guide for deploying the LinuxONE RAG Knowledge Assistant on IBM LinuxONE (s390x architecture).

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Architecture Overview](#architecture-overview)
3. [Pre-Installation Setup](#pre-installation-setup)
4. [Database Setup](#database-setup)
5. [Backend Deployment](#backend-deployment)
6. [Frontend Deployment](#frontend-deployment)
7. [Nginx Configuration](#nginx-configuration)
8. [Service Management](#service-management)
9. [Monitoring and Logs](#monitoring-and-logs)
10. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Operating System
- **Ubuntu 22.04 LTS** or **RHEL 9** on s390x architecture
- Minimum 4 CPU cores
- Minimum 8GB RAM (16GB recommended)
- Minimum 50GB disk space

### Required Software
```bash
# System packages
sudo apt update
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql-15 \
    postgresql-contrib \
    nginx \
    git \
    build-essential
```

### Optional (for AI features)
```bash
# Only if enabling local embeddings/reranking
sudo apt install -y \
    python3.11-dev \
    libpq-dev \
    cargo \
    rustc
```

---

## Architecture Overview

### Production Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    LinuxONE Server                       │
│                                                          │
│  ┌────────────┐    ┌──────────────┐   ┌──────────────┐ │
│  │   Nginx    │───▶│   Backend    │──▶│  PostgreSQL  │ │
│  │  (Port 80) │    │  (Port 8000) │   │  + pgvector  │ │
│  └────────────┘    └──────────────┘   └──────────────┘ │
│        │                   │                            │
│        │                   │                            │
│        ▼                   ▼                            │
│  ┌────────────┐    ┌──────────────┐                    │
│  │  Frontend  │    │  External    │                    │
│  │   (dist/)  │    │  LLM (BOB)   │◀───────────────────┤
│  └────────────┘    └──────────────┘    Internet        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **External LLM**: Uses BOB API for generation (no local Ollama/Qwen needed)
2. **Optional AI**: Local embeddings/reranking are optional (can use precomputed)
3. **Single Endpoint**: Nginx reverse proxy provides unified access
4. **Auto-Start**: Systemd manages backend service lifecycle

---

## Pre-Installation Setup

### 1. Create Application User

```bash
sudo useradd -r -m -d /opt/linuxone-rag -s /bin/bash linuxone-rag
sudo usermod -aG sudo linuxone-rag  # Optional: for admin tasks
```

### 2. Clone Repository

```bash
sudo -u linuxone-rag git clone https://github.com/your-org/LinuxONERAGPipeline.git /opt/linuxone-rag
cd /opt/linuxone-rag
```

### 3. Create Python Virtual Environment

```bash
sudo -u linuxone-rag python3.11 -m venv /opt/linuxone-rag/venv
source /opt/linuxone-rag/venv/bin/activate
```

---

## Database Setup

### 1. Install PostgreSQL with pgvector

```bash
# Install PostgreSQL 15
sudo apt install -y postgresql-15 postgresql-contrib

# Install pgvector extension
sudo apt install -y postgresql-15-pgvector

# Or build from source if not available
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### 2. Create Database and User

```bash
sudo -u postgres psql << EOF
CREATE USER raguser WITH PASSWORD 'your_secure_password';
CREATE DATABASE linuxone_rag OWNER raguser;
\c linuxone_rag
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL PRIVILEGES ON DATABASE linuxone_rag TO raguser;
EOF
```

### 3. Initialize Database Schema

```bash
cd /opt/linuxone-rag/backend
source /opt/linuxone-rag/venv/bin/activate
python -c "from app.models.db_connection import init_db; init_db()"
```

---

## Backend Deployment

### 1. Install Base Dependencies

```bash
cd /opt/linuxone-rag/backend
source /opt/linuxone-rag/venv/bin/activate

# Install runtime dependencies (always required)
pip install -r requirements-base.txt
```

### 2. Optional: Install AI Dependencies

```bash
# Only if you want local embeddings/reranking
# WARNING: Some packages may fail on s390x
pip install -r requirements-ai.txt

# If installation fails, set feature flags to false in .env:
# ENABLE_LOCAL_EMBEDDINGS=false
# ENABLE_LOCAL_RERANKING=false
```

### 3. Configure Environment

```bash
cd /opt/linuxone-rag
cp .env.production.example .env

# Edit .env with actual values
nano .env
```

**Required settings:**
```bash
# LLM Provider
LLM_PROVIDER=external
BOB_API_KEY=your_actual_bob_api_key

# Database
DATABASE_URL=postgresql://raguser:your_secure_password@localhost:5432/linuxone_rag

# Application
FRONTEND_URL=https://your-linuxone-domain.com
```

### 4. Test Backend

```bash
cd /opt/linuxone-rag/backend
source /opt/linuxone-rag/venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Test in another terminal:
curl http://localhost:8000/api/health
```

---

## Frontend Deployment

### 1. Install Node.js

```bash
# Install Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2. Build Frontend

```bash
cd /opt/linuxone-rag/frontend
npm install
npm run build

# Output will be in: frontend/dist/
```

### 3. Set Permissions

```bash
sudo chown -R linuxone-rag:linuxone-rag /opt/linuxone-rag/frontend/dist
```

---

## Nginx Configuration

### 1. Install and Configure Nginx

```bash
# Copy configuration
sudo cp /opt/linuxone-rag/deploy/nginx/linuxone-rag.conf /etc/nginx/sites-available/

# Edit configuration
sudo nano /etc/nginx/sites-available/linuxone-rag.conf
# Update: server_name your-linuxone-domain.com

# Enable site
sudo ln -s /etc/nginx/sites-available/linuxone-rag.conf /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 2. Optional: Setup SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-linuxone-domain.com

# Certbot will automatically update Nginx config
```

---

## Service Management

### 1. Install Systemd Service

```bash
# Copy service file
sudo cp /opt/linuxone-rag/deploy/systemd/linuxone-rag-backend.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable linuxone-rag-backend

# Start service
sudo systemctl start linuxone-rag-backend

# Check status
sudo systemctl status linuxone-rag-backend
```

### 2. Service Commands

```bash
# Start
sudo systemctl start linuxone-rag-backend

# Stop
sudo systemctl stop linuxone-rag-backend

# Restart
sudo systemctl restart linuxone-rag-backend

# View logs
sudo journalctl -u linuxone-rag-backend -f

# View recent logs
sudo journalctl -u linuxone-rag-backend -n 100
```

---

## Monitoring and Logs

### Application Logs

```bash
# Backend logs (systemd journal)
sudo journalctl -u linuxone-rag-backend -f

# Nginx access logs
sudo tail -f /var/log/nginx/linuxone-rag-access.log

# Nginx error logs
sudo tail -f /var/log/nginx/linuxone-rag-error.log
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/api/health

# Full system health (via Nginx)
curl https://your-linuxone-domain.com/api/health
```

### Database Monitoring

```bash
# PostgreSQL status
sudo systemctl status postgresql

# Active connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='linuxone_rag';"

# Database size
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('linuxone_rag'));"
```

---

## Troubleshooting

### Backend Won't Start

**Check logs:**
```bash
sudo journalctl -u linuxone-rag-backend -n 50
```

**Common issues:**

1. **Import errors (AI packages)**
   - Solution: Set `ENABLE_LOCAL_EMBEDDINGS=false` in `.env`
   - Install only `requirements-base.txt`

2. **Database connection failed**
   - Check PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify credentials in `.env`
   - Test connection: `psql $DATABASE_URL`

3. **Port already in use**
   - Check what's using port 8000: `sudo lsof -i :8000`
   - Change port in `.env` and systemd service

### Frontend Not Loading

**Check Nginx:**
```bash
sudo nginx -t
sudo systemctl status nginx
```

**Common issues:**

1. **404 errors**
   - Verify frontend built: `ls /opt/linuxone-rag/frontend/dist`
   - Check Nginx root path in config

2. **API calls failing**
   - Check backend is running: `curl http://localhost:8000/api/health`
   - Verify Nginx proxy settings

### External LLM Errors

**Test BOB API:**
```bash
curl -X POST https://api.bob.build/v1/chat/completions \
  -H "Authorization: Bearer $BOB_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"test"}]}'
```

**Common issues:**

1. **Invalid API key**
   - Verify `BOB_API_KEY` in `.env`
   - Check key hasn't expired

2. **Timeout errors**
   - Increase timeout in Nginx config
   - Check network connectivity

### Performance Issues

**Check resource usage:**
```bash
# CPU and memory
htop

# Disk I/O
iostat -x 1

# Network
iftop
```

**Optimization tips:**

1. **Increase workers** in systemd service (default: 4)
2. **Enable caching** in Nginx for static assets
3. **Tune PostgreSQL** connection pool settings
4. **Monitor query performance** with slow query log

---

## Maintenance

### Updating the Application

```bash
# Stop service
sudo systemctl stop linuxone-rag-backend

# Pull latest code
cd /opt/linuxone-rag
sudo -u linuxone-rag git pull

# Update dependencies
source venv/bin/activate
pip install -r backend/requirements-base.txt

# Rebuild frontend
cd frontend
npm install
npm run build

# Restart service
sudo systemctl start linuxone-rag-backend
```

### Database Backups

```bash
# Create backup
sudo -u postgres pg_dump linuxone_rag > /opt/backups/linuxone_rag_$(date +%Y%m%d).sql

# Restore backup
sudo -u postgres psql linuxone_rag < /opt/backups/linuxone_rag_20260617.sql
```

---

## Security Checklist

- [ ] Change default database password
- [ ] Secure BOB_API_KEY (never commit to git)
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure firewall (ufw/iptables)
- [ ] Regular security updates: `sudo apt update && sudo apt upgrade`
- [ ] Monitor logs for suspicious activity
- [ ] Implement rate limiting in Nginx
- [ ] Regular database backups

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/LinuxONERAGPipeline/issues
- Documentation: See README.md and other docs/ files

---

**Deployment Complete!** 🎉

Your LinuxONE RAG Knowledge Assistant is now running in production.