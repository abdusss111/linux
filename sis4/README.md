# SIS4 - Docker, Systemd Services & Scheduled Tasks

**Student:** Abdurakhimov Abdussalam  
**Assignment:** Working with services - Docker containers, systemd services, and cron jobs

## Overview

This directory contains all the scripts and configurations for SIS4 tasks:

1. **Docker Images** - Container images for frontend and backend services
2. **Systemd Services** - Unit files for automatic container management
3. **Cron Jobs** - Scheduled maintenance scripts

## Directory Structure

```
sis4/
├── README.md
├── systemd/
│   ├── dapmeet-frontend.service    # VM1 - Frontend container service
│   └── dapmeet-backend.service     # VM2 - Backend container service
├── cron/
│   ├── frontend/
│   │   ├── backup_frontend_logs.sh # Daily log backup (2:00 AM)
│   │   └── check_ssl_renewal.sh    # Weekly SSL check (Mon 6:00 AM)
│   └── backend/
│       ├── backup_postgres.sh      # Daily DB backup (3:00 AM)
│       ├── cleanup_processing.sh   # Daily cleanup (4:30 AM)
│       └── rotate_backend_logs.sh  # Weekly log rotation (Sun 5:00 AM)
└── scripts/
    ├── setup_vm1.sh                # Complete VM1 setup script
    ├── setup_vm2.sh                # Complete VM2 setup script
    ├── verify_vm1.sh               # VM1 verification script
    └── verify_vm2.sh               # VM2 verification script
```

## Docker Images

| Image | Docker Hub | Purpose |
|-------|------------|---------|
| dapmeet-client | [abdusss111/dapmeet-client](https://hub.docker.com/r/abdusss111/dapmeet-client) | Next.js Frontend |
| dapmeet-service | [abdusss111/dapmeet-service](https://hub.docker.com/r/abdusss111/dapmeet-service) | FastAPI Backend |

## Quick Start

### VM1 (Frontend) Setup

```bash
# Copy files to VM1 and run:
sudo bash scripts/setup_vm1.sh

# Verify setup:
sudo bash scripts/verify_vm1.sh

# Start service:
sudo systemctl start dapmeet-frontend
```

### VM2 (Backend) Setup

```bash
# Copy files to VM2 and run:
sudo bash scripts/setup_vm2.sh

# Verify setup:
sudo bash scripts/verify_vm2.sh

# Start service:
sudo systemctl start dapmeet-backend
```

## Systemd Services

### Frontend Service (VM1)

```bash
# Service management
sudo systemctl start dapmeet-frontend
sudo systemctl stop dapmeet-frontend
sudo systemctl restart dapmeet-frontend
sudo systemctl status dapmeet-frontend

# View logs
sudo journalctl -u dapmeet-frontend -f
sudo docker logs dapmeet-frontend
```

### Backend Service (VM2)

```bash
# Service management
sudo systemctl start dapmeet-backend
sudo systemctl stop dapmeet-backend
sudo systemctl restart dapmeet-backend
sudo systemctl status dapmeet-backend

# View logs
sudo journalctl -u dapmeet-backend -f
sudo docker logs dapmeet-backend
```

### Service Features

- **Auto-restart**: Services restart automatically on failure
- **Boot startup**: Services start on system boot
- **Health checks**: Container health monitoring
- **Graceful shutdown**: 30-second timeout for clean stops

## Cron Jobs Schedule

| Script | VM | Schedule | Purpose |
|--------|------|----------|---------|
| backup_frontend_logs.sh | VM1 | Daily 2:00 AM | Backup nginx & app logs |
| check_ssl_renewal.sh | VM1 | Mon 6:00 AM | Check SSL cert expiry |
| backup_postgres.sh | VM2 | Daily 3:00 AM | PostgreSQL backup |
| cleanup_processing.sh | VM2 | Daily 4:30 AM | Clean old temp files |
| rotate_backend_logs.sh | VM2 | Sun 5:00 AM | Rotate & compress logs |

### Manual Cron Script Execution

```bash
# Test cron scripts manually
sudo /opt/dapmeet/scripts/cron/backup_frontend_logs.sh
sudo /opt/dapmeet/scripts/cron/backup_postgres.sh

# View cron logs
tail -f /var/log/dapmeet/cron.log
```

## Verification

Both VMs have verification scripts that check:

- ✅ Docker installation and service status
- ✅ Systemd service configuration
- ✅ Cron scripts installation and permissions
- ✅ Crontab configuration
- ✅ Directory structure
- ✅ Required dependencies

## Backup Locations

| Type | Location | Retention |
|------|----------|-----------|
| Frontend Logs | `/var/backups/dapmeet/logs/` | 30 days |
| PostgreSQL | `/var/backups/dapmeet/postgresql/` | 7 days |

## Troubleshooting

### Docker Issues

```bash
# Check Docker status
sudo systemctl status docker
sudo docker info

# View container logs
sudo docker logs dapmeet-frontend
sudo docker logs dapmeet-backend

# Restart Docker
sudo systemctl restart docker
```

### Service Won't Start

```bash
# Check service status
sudo systemctl status dapmeet-frontend

# View detailed logs
sudo journalctl -u dapmeet-frontend -n 50 --no-pager

# Check for configuration errors
sudo systemctl cat dapmeet-frontend
```

### Cron Jobs Not Running

```bash
# Check cron service
sudo systemctl status cron

# View cron logs
grep CRON /var/log/syslog

# Test script manually
sudo bash /opt/dapmeet/scripts/cron/backup_frontend_logs.sh
```

## Key Learning Outcomes

- Multi-server Docker containerization
- Systemd service management for containers
- Auto-restart and recovery configuration
- Cron-based automated maintenance
- Log rotation and backup strategies
- Health checks and monitoring


