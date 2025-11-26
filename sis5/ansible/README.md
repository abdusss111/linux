# Dapmeet Ansible Automation

**Student:** Abdurakhimov Abdussalam  
**Program:** Information Systems  
**Assignment:** SIS5 - Automating All Setup

## Overview

This Ansible project automates the complete infrastructure setup for the Dapmeet application as described in SIS 2, 3, and 4.

### Architecture
- **VM1 (Frontend):** Next.js application, Nginx, static assets
- **VM2 (Backend):** FastAPI backend, PostgreSQL database

## Directory Structure

```
ansible/
├── ansible.cfg              # Ansible configuration
├── requirements.yml         # Galaxy dependencies
├── inventory/
│   └── hosts.yml           # Inventory with VM1 and VM2
├── group_vars/
│   ├── all.yml             # Global variables
│   ├── frontend.yml        # VM1-specific variables
│   └── backend.yml         # VM2-specific variables
├── playbooks/
│   ├── site.yml            # Main playbook (both VMs)
│   ├── vm1.yml             # Frontend only
│   └── vm2.yml             # Backend only
└── roles/
    ├── users/              # SIS2: Users and groups
    ├── permissions/        # SIS2: Directory permissions, sudoers
    ├── ssh/                # SIS2: SSH configuration
    ├── firewall/           # SIS3: UFW firewall
    ├── docker/             # SIS4: Docker installation
    ├── services/           # SIS4: Systemd services
    └── cron/               # SIS4: Scheduled tasks
```

## Roles Description

### SIS2 Roles

| Role | Purpose |
|------|---------|
| `users` | Creates groups and users (postgres, nginx, dapmeet-backend, sysadmin, devops_user, etc.) |
| `permissions` | Sets up directory structure, ownership, and sudoers rules |
| `ssh` | Configures SSH with key-based auth, disables root login |

### SIS3 Roles

| Role | Purpose |
|------|---------|
| `firewall` | Configures UFW with allowed ports (22, 80, 443, 8000, 5432) |

### SIS4 Roles

| Role | Purpose |
|------|---------|
| `docker` | Installs Docker, pulls images from Docker Hub |
| `services` | Creates systemd unit files for containers |
| `cron` | Sets up scheduled backup and maintenance tasks |

## Prerequisites

1. **Control Node:** Ansible 2.9+ installed
2. **Target Nodes:** Ubuntu 20.04/22.04 with Python 3
3. **SSH Access:** Key-based authentication configured

## Installation

```bash
# Install Ansible Galaxy dependencies
ansible-galaxy collection install -r requirements.yml

# Verify inventory
ansible-inventory --list -i inventory/hosts.yml
```

## Usage

### Setup Both VMs
```bash
ansible-playbook -i inventory/hosts.yml playbooks/site.yml
```

### Setup Frontend Only (VM1)
```bash
ansible-playbook -i inventory/hosts.yml playbooks/vm1.yml
```

### Setup Backend Only (VM2)
```bash
ansible-playbook -i inventory/hosts.yml playbooks/vm2.yml
```

### Run Specific Tasks with Tags
```bash
# SIS2 tasks only
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --tags "sis2"

# Docker setup only
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --tags "docker"

# Users and SSH only
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --tags "users,ssh"
```

### Check Mode (Dry Run)
```bash
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --check
```

## Configuration

### Update Inventory

Edit `inventory/hosts.yml` to set actual IP addresses:

```yaml
frontend:
  hosts:
    vm1:
      ansible_host: YOUR_VM1_IP

backend:
  hosts:
    vm2:
      ansible_host: YOUR_VM2_IP
```

### Customize Variables

- `group_vars/all.yml`: Global settings (project paths, Docker images)
- `group_vars/frontend.yml`: VM1 users, ports, cron jobs
- `group_vars/backend.yml`: VM2 users, ports, cron jobs

## Tasks Automated

### From SIS2 (Users & Permissions)
- ✅ 12 user roles across 2 VMs
- ✅ Group creation and membership
- ✅ Directory structure with proper ownership
- ✅ Sudoers configuration
- ✅ SSH key-based authentication

### From SIS3 (Networking)
- ✅ UFW firewall configuration
- ✅ Port allowlisting (SSH, HTTP, HTTPS, API, PostgreSQL)

### From SIS4 (Services)
- ✅ Docker installation and configuration
- ✅ Container images from Docker Hub
- ✅ Systemd service units with auto-restart
- ✅ 4 cron jobs for backup/maintenance

## Verification

After running the playbook:

```bash
# Check users
ansible all -m shell -a "cat /etc/passwd | grep dapmeet"

# Check Docker containers
ansible all -m shell -a "docker ps"

# Check systemd services
ansible all -m shell -a "systemctl status dapmeet-*"

# Check cron jobs
ansible all -m shell -a "crontab -l"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify `~/.ssh/automation_key` exists |
| Permission denied | Check sudo access for automation user |
| Docker pull failed | Verify network access and Docker Hub credentials |

## Docker Hub Links

- Frontend: https://hub.docker.com/repository/docker/abdusss111/dapmeet-client
- Backend: https://hub.docker.com/repository/docker/abdusss111/dapmeet-service

## Conclusions

This Ansible automation successfully implements:
1. Complete user and permission management from SIS2
2. Network security with UFW firewall from SIS3
3. Containerized deployment with systemd from SIS4
4. Automated maintenance via cron from SIS4

The infrastructure-as-code approach ensures:
- **Reproducibility:** Identical setups across environments
- **Version Control:** Changes tracked in Git
- **Idempotency:** Safe to run multiple times
- **Documentation:** Self-documenting configuration

