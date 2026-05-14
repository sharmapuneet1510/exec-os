# Deployment and Operations Guide

Guide for deploying ExecOS to production and managing ongoing operations, monitoring, backups, and performance tuning.

## Table of Contents

1. [Deployment Strategies](#deployment-strategies)
2. [Production Setup](#production-setup)
3. [Monitoring and Logging](#monitoring-and-logging)
4. [Backup and Recovery](#backup-and-recovery)
5. [Performance Tuning](#performance-tuning)
6. [Security Hardening](#security-hardening)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance Schedule](#maintenance-schedule)

---

## Deployment Strategies

### Option 1: Desktop Application (Single User)

**Best for:** Personal use, single machine

**Setup:**
```bash
python3 start.py
```

**Advantages:**
- Zero deployment complexity
- No external dependencies
- Simple backup (copy .db file)
- Full local control

**Disadvantages:**
- Single user only
- No remote access
- Manual server restart needed

**Typical Setup:**
```
MacBook/Windows PC
└── command-center/
    ├── start.py
    ├── db/
    └── ~/.commanddesk/execos.db
```

---

### Option 2: Local Network Server

**Best for:** Team on same network, home server

**Setup:**

1. Start server on machine with static IP:
```bash
python3 start.py
```

2. Access from other machines:
```
http://server-ip:8080
```

3. Use process manager for auto-restart:

**systemd (Linux/macOS with Homebrew):**
```ini
# /etc/systemd/system/execos.service
[Unit]
Description=ExecOS Command Center
After=network.target

[Service]
Type=simple
User=username
WorkingDirectory=/home/username/command-center
ExecStart=/usr/bin/python3 start.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable execos
sudo systemctl start execos
sudo systemctl status execos
```

**macOS (launchd):**
```xml
<!-- ~/Library/LaunchAgents/com.execos.server.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.execos.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/username/command-center/start.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/Users/username/command-center</string>
</dict>
</plist>
```

Enable:
```bash
launchctl load ~/Library/LaunchAgents/com.execos.server.plist
```

---

### Option 3: Cloud Deployment (AWS/GCP/Azure)

**Best for:** Remote team access, high availability

#### AWS EC2 Deployment

1. **Launch EC2 Instance:**
   - OS: Ubuntu 22.04 LTS
   - Instance: t3.medium (minimum)
   - Storage: 20 GB SSD
   - Security Group: Allow 8080, 443, 22

2. **Install on Instance:**
```bash
ssh -i key.pem ubuntu@instance-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install -y python3.11 python3.11-venv git

# Clone repository
git clone https://github.com/user/command-center.git
cd command-center

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start with systemd
sudo cp systemd/execos.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable execos
sudo systemctl start execos
```

3. **Setup Reverse Proxy (nginx):**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

4. **Enable HTTPS (Let's Encrypt):**
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

5. **Setup PostgreSQL Database:**
```bash
sudo apt install -y postgresql

# Create database
sudo -u postgres psql
CREATE DATABASE execos_db;
CREATE USER execos_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE execos_db TO execos_user;
\q

# Update environment
export DATABASE_URL=postgresql://execos_user:secure_password@localhost/execos_db
```

---

### Option 4: Docker Deployment

**Best for:** Container orchestration, Kubernetes

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /data

# Expose port
EXPOSE 8080

# Environment
ENV DATABASE_URL=sqlite:////data/execos.db
ENV PORT=8080

# Run
CMD ["python3", "web_server.py"]
```

**Docker Compose:**
```yaml
version: '3.8'

services:
  execos:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - execos-data:/data
    environment:
      DATABASE_URL: sqlite:////data/execos.db
      PORT: 8080
    restart: unless-stopped

volumes:
  execos-data:
```

Build and run:
```bash
docker-compose up -d
docker-compose logs -f
```

---

## Production Setup

### Database

#### Option 1: SQLite (Development/Small Teams)

**Best for:** < 10 users, < 1 million records

```bash
# Default location
~/.commanddesk/execos.db

# Backup strategy
tar -czf execos_db_backup_$(date +%Y%m%d).tar.gz ~/.commanddesk/
```

#### Option 2: PostgreSQL (Production/Large Teams)

**Best for:** Multiple users, enterprise deployment

1. **Install PostgreSQL:**
```bash
# Ubuntu
sudo apt install -y postgresql postgresql-contrib

# macOS
brew install postgresql
```

2. **Create Database and User:**
```bash
sudo -u postgres psql

CREATE DATABASE execos_db;
CREATE USER execos_user WITH PASSWORD 'secure_password';
ALTER ROLE execos_user SET client_encoding TO 'utf8';
ALTER ROLE execos_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE execos_user SET default_transaction_deferrable TO on;
ALTER ROLE execos_user SET default_transaction_read_only TO off;
ALTER ROLE execos_user SET timezone TO 'UTC';

GRANT ALL PRIVILEGES ON DATABASE execos_db TO execos_user;
\q
```

3. **Update Connection:**
```bash
# Set in environment or .env
DATABASE_URL=postgresql://execos_user:secure_password@localhost:5432/execos_db
```

4. **Initialize Schema:**
```bash
python3 -c "from db.init_db import create_all; create_all()"
```

### Web Server Configuration

#### nginx Reverse Proxy

```nginx
upstream execos {
    server localhost:8080;
    keepalive 32;
}

server {
    listen 80;
    listen 443 ssl http2;
    server_name execos.example.com;

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/execos.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/execos.example.com/privkey.pem;

    # Performance
    client_max_body_size 100M;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # Logging
    access_log /var/log/nginx/execos_access.log;
    error_log /var/log/nginx/execos_error.log;

    # Proxy settings
    location / {
        proxy_pass http://execos;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Redirect HTTP to HTTPS
    if ($scheme != "https") {
        return 301 https://$server_name$request_uri;
    }
}
```

---

## Monitoring and Logging

### Application Logging

#### Configure Log Level

```bash
# Set in environment
export LOG_LEVEL=debug  # debug, info, warning, error

# Or in .env
LOG_LEVEL=info
```

#### View Logs

```bash
# Systemd
sudo journalctl -u execos -f

# Docker
docker-compose logs -f execos

# Direct file
tail -f /var/log/execos/app.log
```

### Database Monitoring

#### Query Slow Queries

```sql
-- PostgreSQL
SELECT query, calls, mean_exec_time, max_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- SQLite (use EXPLAIN QUERY PLAN)
EXPLAIN QUERY PLAN
SELECT * FROM tasks WHERE due_date < date('now');
```

#### Connection Monitoring

```sql
-- PostgreSQL
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;

-- Active connections
SELECT pid, usename, application_name, state 
FROM pg_stat_activity 
WHERE datname = 'execos_db';
```

### Health Checks

#### API Health Endpoint

```bash
curl -f http://localhost:8080/health || exit 1
```

#### Automated Health Monitoring

```bash
#!/bin/bash
# health_check.sh

while true; do
    response=$(curl -s http://localhost:8080/health)
    if [[ $response == *'"status":"ok"'* ]]; then
        echo "[$(date)] Health check passed"
    else
        echo "[$(date)] Health check FAILED - restarting service"
        systemctl restart execos
    fi
    sleep 300  # Check every 5 minutes
done
```

Run in background:
```bash
nohup ./health_check.sh > /var/log/execos_health.log 2>&1 &
```

---

## Backup and Recovery

### Automated Daily Backups

#### For SQLite

```bash
#!/bin/bash
# backup_execos.sh

BACKUP_DIR="/backups/execos"
DB_PATH="$HOME/.commanddesk/execos.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
cp "$DB_PATH" "$BACKUP_DIR/execos_$DATE.db"

# Keep only last 30 days
find "$BACKUP_DIR" -name "execos_*.db" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/execos_$DATE.db"
```

Add to crontab:
```bash
crontab -e
# Add line:
0 2 * * * /home/user/backup_execos.sh >> /var/log/execos_backup.log 2>&1
```

#### For PostgreSQL

```bash
#!/bin/bash
# backup_postgres.sh

BACKUP_DIR="/backups/execos"
DB_NAME="execos_db"
DB_USER="execos_user"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
pg_dump -U "$DB_USER" -d "$DB_NAME" -F c -f "$BACKUP_DIR/execos_$DATE.dump"

# Compress
gzip "$BACKUP_DIR/execos_$DATE.dump"

# Keep only last 30 days
find "$BACKUP_DIR" -name "execos_*.dump.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/execos_$DATE.dump.gz"
```

### Recovery Procedures

#### Restore from SQLite Backup

```bash
# Stop the application
systemctl stop execos

# Restore
cp /backups/execos/execos_20260514_020000.db ~/.commanddesk/execos.db

# Restart
systemctl start execos
```

#### Restore from PostgreSQL Backup

```bash
# Stop application
systemctl stop execos

# Drop and recreate database
sudo -u postgres psql -c "DROP DATABASE execos_db;"
sudo -u postgres psql -c "CREATE DATABASE execos_db;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE execos_db TO execos_user;"

# Restore
gunzip -c /backups/execos/execos_20260514_020000.dump.gz | \
  pg_restore -U execos_user -d execos_db

# Restart
systemctl start execos
```

---

## Performance Tuning

### Database Optimization

#### Add Indexes (PostgreSQL)

```sql
-- For frequent queries
CREATE INDEX idx_tasks_due_date ON tasks(due_date DESC);
CREATE INDEX idx_tasks_status_priority ON tasks(status, priority);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_activity_logs_created ON activity_logs(created_at DESC);
```

#### Analyze Query Plans

```sql
-- PostgreSQL
EXPLAIN ANALYZE
SELECT * FROM tasks WHERE due_date < CURRENT_DATE AND status != 'done';
```

### API Performance

#### Enable Response Compression

Already enabled in FastAPI via gzip middleware.

#### Adjust Cache Duration

In `web/deps.py`:
```python
CACHE_TTL = 60  # Seconds
```

Increase for better performance, decrease for fresher data.

### Memory Optimization

#### Monitor Resource Usage

```bash
# Real-time monitoring
htop

# Memory usage
ps aux | grep python3

# Database file size
ls -lh ~/.commanddesk/execos.db
du -sh /var/lib/postgresql/
```

#### Clean Up Old Records

```sql
-- Archive completed tasks older than 1 year
DELETE FROM tasks 
WHERE status = 'done' 
AND completed_at < NOW() - INTERVAL '1 year';

-- Delete old activity logs
DELETE FROM activity_logs 
WHERE created_at < NOW() - INTERVAL '90 days';
```

---

## Security Hardening

### Network Security

#### Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw deny 8080         # Block direct access to app port
sudo ufw enable
```

#### Rate Limiting

Implement in nginx:
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

server {
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://execos;
    }
}
```

### Database Security

#### PostgreSQL

```sql
-- Create read-only user for reporting
CREATE ROLE execos_readonly WITH LOGIN PASSWORD 'password';
GRANT CONNECT ON DATABASE execos_db TO execos_readonly;
GRANT USAGE ON SCHEMA public TO execos_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO execos_readonly;

-- Prevent password auth if using trust method
```

#### Encryption at Rest

```bash
# SQLite - Use database encryption (SQLCipher) for sensitive data
# PostgreSQL - Enable SSL connections
```

### Application Security

#### HTTPS/TLS

```bash
# Generate self-signed cert for testing
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Use Let's Encrypt for production (see nginx config above)
```

#### Authentication (Future)

```python
# Coming in Phase 2
# - API Key authentication
# - JWT tokens
# - User session management
```

---

## Troubleshooting

### Common Production Issues

#### Service Won't Start

```bash
# Check logs
sudo journalctl -u execos -n 50

# Verify Python and dependencies
python3 --version
pip list | grep fastapi

# Check port availability
netstat -tuln | grep 8080
```

#### High Memory Usage

```bash
# Check process
ps aux | grep python3

# Identify memory leaks
# In app logs or monitoring

# Solution: Restart service and investigate
systemctl restart execos

# Database cleanup
python3 -c "
from db.base import SessionLocal
db = SessionLocal()
# Run cleanup queries
db.close()
"
```

#### Database Corruption

**SQLite:**
```bash
# Integrity check
sqlite3 ~/.commanddesk/execos.db "PRAGMA integrity_check;"

# Repair (rewrite)
sqlite3 ~/.commanddesk/execos.db "VACUUM;"

# Restore from backup if corrupted
```

**PostgreSQL:**
```bash
# Check integrity
sudo -u postgres pg_check_connection 

# Check for bloat
sudo -u postgres vacuumdb -U execos_user execos_db
sudo -u postgres reindexdb -U execos_user execos_db
```

---

## Maintenance Schedule

### Daily

- [ ] Monitor error logs
- [ ] Health check passes
- [ ] Backup completed

### Weekly

- [ ] Database backup integrity check
- [ ] API response times acceptable
- [ ] No unresolved alerts

### Monthly

- [ ] Database optimization (VACUUM, ANALYZE)
- [ ] Old log cleanup
- [ ] Archive completed tasks/projects
- [ ] Review and update backups

### Quarterly

- [ ] Full security audit
- [ ] Performance analysis
- [ ] Dependency updates
- [ ] Disaster recovery drill

---

## Deployment Checklist

- [ ] Database configured and tested
- [ ] Web server (nginx/Apache) configured
- [ ] SSL certificates installed
- [ ] Backup strategy in place
- [ ] Monitoring and alerting configured
- [ ] Logs being collected
- [ ] Security hardening complete
- [ ] Team trained on operations
- [ ] Runbooks documented
- [ ] Disaster recovery tested

