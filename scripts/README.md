# Dapmeet Infrastructure Setup Scripts

Complete, idempotent setup scripts for the Dapmeet 2-VM architecture.

## Overview

These scripts automate the complete setup of the Dapmeet infrastructure based on all SIS implementations:

| SIS | Topic | Included |
|-----|-------|----------|
| SIS1 | Project Introduction | Architecture definitions |
| SIS2 | Users & Permissions | Groups, users, sudoers, directories |
| SIS3 | Networking | Packages, firewall, Node.js |
| SIS4 | Services | Docker, PostgreSQL, systemd, cron |
| SIS5 | Ansible | Can be used instead of these scripts |
| SIS6 | Journaling | journald configuration |

## Structure

```
scripts/
├── common/
│   └── lib.sh              # Shared library functions
├── vm1/
│   └── main.sh             # Complete VM1 (Frontend) setup
├── vm2/
│   └── main.sh             # Complete VM2 (Backend) setup
└── README.md               # This file
```

## Features

### Idempotent Operations

All scripts are designed to be **idempotent** - running them multiple times produces the same result:

- ✅ Groups only created if they don't exist
- ✅ Users only created if they don't exist
- ✅ Packages only installed if not present
- ✅ Docker only installed if not available
- ✅ Services enabled without errors if already enabled
- ✅ Firewall rules added without duplicates
- ✅ Directories created with proper permissions

### Safe Execution

```bash
# Scripts will skip existing configurations
[SKIP] Group 'dapmeet' already exists
[SKIP] User 'automation' already exists
[SKIP] Docker is already installed: Docker version 24.0.7
[SKIP] Package 'nginx' is already installed
```

## Usage

### VM1 (Frontend Server)

```bash
# Copy scripts to VM1
scp -r scripts/ user@vm1:/tmp/

# SSH to VM1 and run
ssh user@vm1
cd /tmp/scripts/vm1
sudo bash main.sh
```

**Options:**
```bash
sudo bash main.sh --help           # Show help
sudo bash main.sh --skip-docker-pull  # Skip Docker image pull
sudo bash main.sh --verbose        # Enable verbose output
```

### VM2 (Backend Server)

```bash
# Copy scripts to VM2
scp -r scripts/ user@vm2:/tmp/

# SSH to VM2 and run
ssh user@vm2
cd /tmp/scripts/vm2
sudo bash main.sh
```

**Options:**
```bash
sudo bash main.sh --help              # Show help
sudo bash main.sh --skip-docker-pull  # Skip Docker image pull
sudo bash main.sh --skip-db-setup     # Skip PostgreSQL database creation
sudo bash main.sh --verbose           # Enable verbose output
```

**Environment Variables:**
```bash
# Set custom database password
export DAPMEET_DB_PASSWORD="your_secure_password"
sudo bash main.sh
```

## What Gets Installed

### VM1 (Frontend)

| Component | Details |
|-----------|---------|
| **Users** | nginx, deployer, sysadmin, devops_user, automation, monitoring, auditor |
| **Groups** | www-data, deployer, sysadmin, devops, automation, monitoring, auditor, dapmeet |
| **Packages** | nginx, nodejs, docker, certbot, fail2ban, ufw |
| **Services** | nginx, docker, fail2ban, dapmeet-frontend |
| **Cron Jobs** | Log backup (daily), SSL check (weekly) |
| **Firewall** | SSH, HTTP, HTTPS, port 3000 |

### VM2 (Backend)

| Component | Details |
|-----------|---------|
| **Users** | dapmeet-backend, dapmeet-worker, sysadmin, devops_user, dba_user, automation, monitoring, backup, auditor |
| **Groups** | postgres, dapmeet, dba, backup, sysadmin, devops, automation, monitoring, auditor |
| **Packages** | postgresql, docker, python3, fail2ban, ufw, logrotate |
| **Services** | postgresql, docker, fail2ban, dapmeet-backend |
| **Cron Jobs** | PostgreSQL backup (daily), cleanup (daily), log rotation (weekly) |
| **Firewall** | SSH, port 8000 (API), port 5432 (PostgreSQL) |
| **Database** | dapmeet database with dapmeet user |

## Directory Structure Created

### VM1
```
/opt/dapmeet/
├── frontend/           # Application files
└── scripts/cron/       # Cron scripts

/var/log/dapmeet/       # Application logs
/var/backups/dapmeet/   # Backups
/etc/dapmeet/
├── nginx/              # Nginx configs
└── ssl/                # SSL certificates
```

### VM2
```
/opt/dapmeet/
├── backend/            # Backend application
├── worker/             # Worker processes
└── scripts/cron/       # Cron scripts

/var/dapmeet/
├── processing/         # Temporary processing files
└── uploads/            # User uploads

/var/log/dapmeet/       # Application logs
/var/backups/dapmeet/
└── postgresql/         # Database backups

/etc/dapmeet/backend/   # Backend configs
```

## Post-Setup Steps

### VM1 (Frontend)

1. Create environment file:
```bash
sudo vim /opt/dapmeet/frontend/.env
# Add your environment variables
```

2. Start the service:
```bash
sudo systemctl start dapmeet-frontend
sudo systemctl status dapmeet-frontend
```

3. (Optional) Configure SSL with Certbot:
```bash
sudo certbot --nginx -d your-domain.com
```

### VM2 (Backend)

1. Update database password in systemd service (if changed):
```bash
sudo vim /etc/systemd/system/dapmeet-backend.service
# Update DATABASE_URL
sudo systemctl daemon-reload
```

2. Start the service:
```bash
sudo systemctl start dapmeet-backend
sudo systemctl status dapmeet-backend
```

3. Test database connection:
```bash
sudo -u postgres psql -d dapmeet -c "SELECT 1;"
```

## Verification

### Check installation status:
```bash
# VM1
sudo systemctl status dapmeet-frontend
sudo docker ps
sudo ufw status

# VM2
sudo systemctl status dapmeet-backend
sudo systemctl status postgresql
sudo docker ps
```

### View logs:
```bash
# Service logs
sudo journalctl -u dapmeet-frontend -f
sudo journalctl -u dapmeet-backend -f

# Container logs
sudo docker logs dapmeet-frontend
sudo docker logs dapmeet-backend
```

## Integration with Other SIS Tasks

### With SIS5 (Ansible)
You can use Ansible instead of these scripts:
```bash
cd sis5/ansible
ansible-playbook -i inventory/hosts.yml playbooks/site.yml
```

### With Bonus Tasks

**Bonus 1 (CI/CD):**
These scripts can be called from GitHub Actions:
```yaml
- name: Run setup
  run: |
    scp -r scripts/ ${{ secrets.VM_USER }}@${{ secrets.VM_HOST }}:/tmp/
    ssh ${{ secrets.VM_USER }}@${{ secrets.VM_HOST }} "sudo bash /tmp/scripts/vm1/main.sh"
```

**Bonus 2 (Terraform):**
After Terraform creates VMs, run these scripts to configure them:
```bash
terraform apply
terraform output ssh_frontend  # Get SSH command
# Then run main.sh on the created VMs
```

## Troubleshooting

### Script fails with permission error
```bash
# Ensure running as root
sudo bash main.sh
```

### Docker installation fails
```bash
# Check internet connectivity
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | head -c 100

# Manual install
apt-get update && apt-get install docker.io -y
```

### PostgreSQL connection issues
```bash
# Check service
sudo systemctl status postgresql

# Check logs
sudo journalctl -u postgresql -f

# Verify user exists
sudo -u postgres psql -c "\\du"
```

### Firewall blocking connections
```bash
# Check status
sudo ufw status verbose

# Allow additional port
sudo ufw allow 8080/tcp
```

## Common Library Functions (lib.sh)

The common library provides these reusable functions:

| Function | Description |
|----------|-------------|
| `ensure_group` | Create group if not exists |
| `ensure_user` | Create user if not exists |
| `ensure_user_in_group` | Add user to group |
| `ensure_directory` | Create directory with permissions |
| `ensure_package` | Install package if not present |
| `ensure_docker` | Install Docker if not present |
| `ensure_nodejs` | Install Node.js if not present |
| `ensure_postgresql` | Install PostgreSQL if not present |
| `ensure_pg_database` | Create database and user |
| `ensure_sudoers` | Create sudoers file |
| `ensure_ufw_rule` | Add firewall rule |
| `ensure_service_running` | Enable and start service |

Example usage in custom scripts:
```bash
#!/bin/bash
source /path/to/scripts/common/lib.sh

check_root
ensure_package "htop"
ensure_directory "/var/myapp" "www-data:www-data" "755"
ensure_user "myuser" "mygroup" "/home/myuser" "/bin/bash"
```

