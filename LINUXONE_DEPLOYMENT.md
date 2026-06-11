# LinuxONE Deployment Strategy

## Overview

This document outlines the strategy for migrating the RAG Knowledge Assistant from local development to enterprise LinuxONE deployment, designed for commercial use at events and production environments.

## Deployment Architecture

```mermaid
graph TB
    subgraph "LinuxONE Infrastructure"
        subgraph "Application Layer"
            LB[Load Balancer]
            API1[FastAPI Instance 1]
            API2[FastAPI Instance 2]
            API3[FastAPI Instance 3]
        end
        
        subgraph "Data Layer"
            PG_PRIMARY[PostgreSQL Primary]
            PG_REPLICA1[PostgreSQL Replica 1]
            PG_REPLICA2[PostgreSQL Replica 2]
        end
        
        subgraph "ML Services"
            EMB1[Embedding Service 1]
            EMB2[Embedding Service 2]
            LLM[Local LLM Service]
        end
        
        subgraph "Frontend"
            WEB[Web Server - Nginx]
            REACT[React App]
        end
    end
    
    LB --> API1
    LB --> API2
    LB --> API3
    
    API1 --> PG_PRIMARY
    API2 --> PG_PRIMARY
    API3 --> PG_PRIMARY
    
    PG_PRIMARY --> PG_REPLICA1
    PG_PRIMARY --> PG_REPLICA2
    
    API1 --> EMB1
    API2 --> EMB2
    API3 --> EMB1
    
    API1 --> LLM
    API2 --> LLM
    API3 --> LLM
    
    WEB --> REACT
    WEB --> LB
    
    style LB fill:#4CAF50
    style PG_PRIMARY fill:#2196F3
    style LLM fill:#FF9800
```

## Migration Phases

### Phase 1: Infrastructure Preparation

#### 1.1 LinuxONE System Setup

**Hardware Requirements:**
- LinuxONE III or LinuxONE Emperor 4
- Minimum 32 cores allocated
- 128GB RAM minimum
- 1TB SSD storage for database
- 500GB for application and models

**Operating System:**
- Red Hat Enterprise Linux 8.x or 9.x for LinuxONE
- Ubuntu 22.04 LTS for LinuxONE (alternative)
- SUSE Linux Enterprise Server 15 SP4+ (alternative)

**Network Configuration:**
```yaml
Network Setup:
  - Internal Network: 10.0.0.0/16
  - DMZ Network: 172.16.0.0/24
  - Management Network: 192.168.1.0/24
  
Firewall Rules:
  - Allow: 443 (HTTPS) from external
  - Allow: 80 (HTTP) from external → redirect to 443
  - Allow: 5432 (PostgreSQL) internal only
  - Allow: 8000 (FastAPI) internal only
  - Allow: 11434 (Ollama) internal only
```

#### 1.2 Container Platform

**Option A: Kubernetes (Recommended for Production)**
```bash
# Install OpenShift on LinuxONE
# Or use upstream Kubernetes

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/s390x/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Verify installation
kubectl version --client
```

**Option B: Docker Swarm (Simpler Alternative)**
```bash
# Initialize Docker Swarm
docker swarm init --advertise-addr <MANAGER-IP>

# Add worker nodes
docker swarm join --token <TOKEN> <MANAGER-IP>:2377
```

**Option C: Podman (Red Hat Preferred)**
```bash
# Install Podman
sudo dnf install podman podman-compose

# Enable Podman socket
systemctl --user enable --now podman.socket
```

### Phase 2: Database Migration

#### 2.1 PostgreSQL Setup on LinuxONE

**Installation:**
```bash
# Install PostgreSQL 15
sudo dnf install postgresql15-server postgresql15-contrib

# Initialize database
sudo postgresql-setup --initdb

# Start and enable service
sudo systemctl start postgresql-15
sudo systemctl enable postgresql-15
```

**pgvector Installation:**
```bash
# Install development tools
sudo dnf install postgresql15-devel gcc git

# Clone and build pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Enable extension
sudo -u postgres psql -c "CREATE EXTENSION vector;"
```

**High Availability Configuration:**

Create `postgresql.conf` for primary:
```conf
# Replication settings
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
hot_standby = on

# Performance tuning for LinuxONE
shared_buffers = 32GB
effective_cache_size = 96GB
maintenance_work_mem = 2GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 64MB
min_wal_size = 2GB
max_wal_size = 8GB
max_worker_processes = 16
max_parallel_workers_per_gather = 4
max_parallel_workers = 16
max_parallel_maintenance_workers = 4
```

**Replication Setup:**
```bash
# On primary server
sudo -u postgres psql -c "CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'secure_password';"

# Configure pg_hba.conf
echo "host replication replicator <replica-ip>/32 md5" | sudo tee -a /var/lib/pgsql/15/data/pg_hba.conf

# On replica servers
sudo -u postgres pg_basebackup -h <primary-ip> -D /var/lib/pgsql/15/data -U replicator -P -v -R -X stream -C -S replica_1
```

#### 2.2 Data Migration

**Export from Local:**
```bash
# Dump local database
pg_dump -h localhost -U raguser -d linuxone_rag -F c -f linuxone_rag_backup.dump

# Or use custom format for large databases
pg_dump -h localhost -U raguser -d linuxone_rag -F d -j 4 -f linuxone_rag_backup
```

**Import to LinuxONE:**
```bash
# Transfer backup to LinuxONE
scp linuxone_rag_backup.dump user@linuxone-server:/tmp/

# Restore on LinuxONE
pg_restore -h localhost -U raguser -d linuxone_rag -j 8 /tmp/linuxone_rag_backup.dump

# Verify data
psql -h localhost -U raguser -d linuxone_rag -c "SELECT COUNT(*) FROM chunks;"
```

### Phase 3: Application Deployment

#### 3.1 Container Images for s390x Architecture

**Build Multi-Architecture Images:**

Create `Dockerfile.backend`:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build for s390x:**
```bash
# Using Docker buildx for multi-arch
docker buildx create --name multiarch --use
docker buildx build --platform linux/s390x -t linuxone-rag-backend:latest -f Dockerfile.backend --push .

# Or build natively on LinuxONE
docker build -t linuxone-rag-backend:latest -f Dockerfile.backend .
```

#### 3.2 Kubernetes Deployment

**Create Namespace:**
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: linuxone-rag
```

**Backend Deployment:**
```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-backend
  namespace: linuxone-rag
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-backend
  template:
    metadata:
      labels:
        app: rag-backend
    spec:
      containers:
      - name: backend
        image: linuxone-rag-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: database-url
        - name: OLLAMA_BASE_URL
          value: "http://ollama-service:11434"
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: rag-backend-service
  namespace: linuxone-rag
spec:
  selector:
    app: rag-backend
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: ClusterIP
```

**Ingress Configuration:**
```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rag-ingress
  namespace: linuxone-rag
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - rag.linuxone.example.com
    secretName: rag-tls
  rules:
  - host: rag.linuxone.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: rag-backend-service
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: rag-frontend-service
            port:
              number: 80
```

#### 3.3 LLM Service Deployment

**Ollama on LinuxONE:**
```yaml
# ollama-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
  namespace: linuxone-rag
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        volumeMounts:
        - name: ollama-data
          mountPath: /root/.ollama
        resources:
          requests:
            memory: "16Gi"
            cpu: "8"
          limits:
            memory: "32Gi"
            cpu: "16"
      volumes:
      - name: ollama-data
        persistentVolumeClaim:
          claimName: ollama-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: ollama-service
  namespace: linuxone-rag
spec:
  selector:
    app: ollama
  ports:
  - protocol: TCP
    port: 11434
    targetPort: 11434
  type: ClusterIP
```

### Phase 4: Security Hardening

#### 4.1 Network Security

**Implement Network Policies:**
```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: rag-network-policy
  namespace: linuxone-rag
spec:
  podSelector:
    matchLabels:
      app: rag-backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: ollama
    ports:
    - protocol: TCP
      port: 11434
```

#### 4.2 Authentication & Authorization

**Implement JWT Authentication:**
```python
# backend/app/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key-from-env"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
```

#### 4.3 Secrets Management

**Using Kubernetes Secrets:**
```bash
# Create secrets
kubectl create secret generic rag-secrets \
  --from-literal=database-url='postgresql://user:pass@host:5432/db' \
  --from-literal=jwt-secret='your-jwt-secret' \
  --namespace=linuxone-rag

# Or use sealed secrets for GitOps
kubeseal --format=yaml < secrets.yaml > sealed-secrets.yaml
```

### Phase 5: Monitoring & Observability

#### 5.1 Prometheus Metrics

**Add Metrics to FastAPI:**
```python
# backend/app/metrics.py
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Response

query_counter = Counter('rag_queries_total', 'Total number of queries')
query_duration = Histogram('rag_query_duration_seconds', 'Query duration')
retrieval_counter = Counter('rag_retrievals_total', 'Total retrievals')

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

#### 5.2 Logging Configuration

**Structured Logging:**
```python
# backend/app/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName
        }
        return json.dumps(log_data)

# Configure logging
logging.basicConfig(level=logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger(__name__)
logger.addHandler(handler)
```

### Phase 6: Performance Optimization

#### 6.1 Caching Strategy

**Redis for Query Caching:**
```yaml
# redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: linuxone-rag
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
```

**Implement Caching:**
```python
# backend/app/cache.py
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='redis-service', port=6379, decode_responses=True)

def cache_query(ttl=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"query:{kwargs.get('query', '')}"
            
            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(cache_key, ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator
```

#### 6.2 Database Optimization

**Connection Pooling:**
```python
# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Phase 7: Disaster Recovery

#### 7.1 Backup Strategy

**Automated Backups:**
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/linuxone-rag"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
pg_dump -h postgres-primary -U raguser -d linuxone_rag -F c -f "$BACKUP_DIR/db_$DATE.dump"

# Compress
gzip "$BACKUP_DIR/db_$DATE.dump"

# Upload to object storage
aws s3 cp "$BACKUP_DIR/db_$DATE.dump.gz" s3://backups/linuxone-rag/

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.dump.gz" -mtime +30 -delete
```

**Schedule with CronJob:**
```yaml
# backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
  namespace: linuxone-rag
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h postgres-primary -U raguser -d linuxone_rag -F c | gzip > /backups/backup_$(date +%Y%m%d).dump.gz
            volumeMounts:
            - name: backup-storage
              mountPath: /backups
          restartPolicy: OnFailure
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
```

## Event Deployment Checklist

### Pre-Event (1 Week Before)

- [ ] Verify all services are running
- [ ] Load test with expected traffic
- [ ] Backup all data
- [ ] Test disaster recovery procedures
- [ ] Verify monitoring and alerting
- [ ] Document runbook for common issues
- [ ] Train support staff

### Event Day

- [ ] Monitor system health dashboard
- [ ] Check resource utilization
- [ ] Verify backup completion
- [ ] Have rollback plan ready
- [ ] Monitor query latency
- [ ] Track error rates
- [ ] Be ready for scaling

### Post-Event

- [ ] Collect metrics and analytics
- [ ] Review logs for issues
- [ ] Document lessons learned
- [ ] Optimize based on usage patterns
- [ ] Update documentation

## Cost Optimization

### Resource Allocation

```yaml
Production Sizing:
  Backend Pods: 3-5 replicas
  Database: Primary + 2 replicas
  LLM Service: 1-2 instances
  Redis Cache: 1 instance
  
Total Resources:
  CPU: 40-60 cores
  Memory: 128-192 GB
  Storage: 2-3 TB
```

### Scaling Strategy

**Horizontal Pod Autoscaler:**
```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rag-backend-hpa
  namespace: linuxone-rag
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rag-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Conclusion

This deployment strategy provides a comprehensive path from local development to enterprise LinuxONE deployment, ensuring:

- **High Availability**: Multiple replicas and database replication
- **Security**: Network policies, authentication, secrets management
- **Performance**: Caching, connection pooling, optimized queries
- **Observability**: Metrics, logging, monitoring
- **Disaster Recovery**: Automated backups and recovery procedures

The system is designed to scale horizontally and handle production workloads while maintaining the flexibility to adapt to specific event requirements.