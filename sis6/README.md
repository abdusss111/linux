# SIS6 - Working with Journals

**Student:** Abdurakhimov Abdussalam  
**Assignment:** SIS6 - Working with journals  
**Topic:** Set up journalling with predefined scripts for specific needs

## Overview

This project implements comprehensive logging, journaling, and auditing for the Dapmeet 2-VM architecture using Ansible automation.

## Tasks Implemented

### Task 1: Setting up journalling everything
Configure all parts of the system to integrate with Linux logging system:
- **systemd-journald** - Persistent journal storage with compression
- **rsyslog** - Log forwarding and custom application logs
- Integration of all services into centralized logging

### Task 2: Creating a toolset of journalling
Scripts for specific use cases of journal watching:
- `journal-search` - Pattern searching in journal logs
- `journal-services` - Filtering and monitoring services  
- `journal-security` - Security event monitoring
- `audit-search` - Audit log searching
- `log-analyzer` - Log analysis and statistics
- `journal-monitor` - Real-time monitoring with alerts
- `daily-report` - Automated daily reports

### Task 3: Setting up auditing events
Custom audit events for security-sensitive actions:
- **Sudoers monitoring** - Changes to `/etc/sudoers` and `/etc/sudoers.d/`
- **Identity changes** - User/group modifications (`/etc/passwd`, `/etc/shadow`, etc.)
- **SSH configuration** - Changes to SSH config files
- **Privileged commands** - Execution of useradd, usermod, passwd, etc.
- **System changes** - Cron jobs, systemd units, kernel modules

## Directory Structure

```
sis6/
├── README.md
├── task.md
└── ansible/
    ├── ansible.cfg
    ├── inventory/
    │   └── hosts.yml
    ├── group_vars/
    │   └── all.yml
    ├── playbooks/
    │   └── site.yml
    └── roles/
        ├── journald/          # Task 1: Journal configuration
        │   ├── tasks/main.yml
        │   ├── templates/
        │   │   ├── journald.conf.j2
        │   │   └── rate-limit.conf.j2
        │   ├── handlers/main.yml
        │   └── meta/main.yml
        ├── rsyslog/           # Task 1: Rsyslog integration
        │   ├── tasks/main.yml
        │   ├── templates/
        │   │   ├── rsyslog.conf.j2
        │   │   ├── imjournal.conf.j2
        │   │   ├── dapmeet.conf.j2
        │   │   ├── security.conf.j2
        │   │   └── logrotate-dapmeet.j2
        │   ├── handlers/main.yml
        │   └── meta/main.yml
        ├── auditd/            # Task 3: Audit configuration
        │   ├── tasks/main.yml
        │   ├── templates/
        │   │   ├── auditd.conf.j2
        │   │   ├── audit.rules.j2
        │   │   ├── sudoers-audit.rules.j2
        │   │   ├── identity-audit.rules.j2
        │   │   ├── privileged-audit.rules.j2
        │   │   ├── syscall-audit.rules.j2
        │   │   └── audisp-syslog.conf.j2
        │   ├── handlers/main.yml
        │   └── meta/main.yml
        └── journal_tools/     # Task 2: Toolset scripts
            ├── tasks/main.yml
            ├── templates/
            │   ├── journal-search.sh.j2
            │   ├── journal-services.sh.j2
            │   ├── journal-security.sh.j2
            │   ├── audit-search.sh.j2
            │   ├── log-analyzer.sh.j2
            │   ├── journal-monitor.sh.j2
            │   └── daily-report.sh.j2
            └── meta/main.yml
```

## Quick Start

### Prerequisites
- Ansible 2.9+
- Target VMs running Debian/Ubuntu
- SSH access configured

### Installation

1. **Update inventory** with your VM IPs:
```bash
vim ansible/inventory/hosts.yml
```

2. **Run the playbook**:
```bash
cd ansible
ansible-playbook playbooks/site.yml
```

3. **Run specific tasks**:
```bash
# Only journald configuration
ansible-playbook playbooks/site.yml --tags journald

# Only auditd (security auditing)
ansible-playbook playbooks/site.yml --tags auditd

# Only install tools
ansible-playbook playbooks/site.yml --tags tools
```

## Usage Examples

### Journal Search
```bash
# Search for pattern
journal-search "Failed password"

# Search with time range
journal-search -s "2 hours ago" -p err "error"

# Predefined searches
journal-search --auth-failures
journal-search --sudo-commands
journal-search --errors
```

### Service Monitoring
```bash
# View service logs
journal-services sshd

# Follow multiple services in real-time
journal-services -f nginx docker

# Service status overview
journal-services --status
```

### Security Monitoring
```bash
# Security summary
journal-security --summary

# All authentication events
journal-security --auth

# Audit events
journal-security --audit

# Full security report
journal-security --all
```

### Audit Log Search
```bash
# Search by key
audit-search sudoers_changes

# Search by user
audit-search -u root -s today

# List all audit keys
audit-search --list-keys

# Audit summary
audit-search --summary
```

### Log Analysis
```bash
# Full analysis
log-analyzer --full

# Error analysis
log-analyzer --errors

# Service analysis
log-analyzer --services
```

### Real-time Monitoring
```bash
# Monitor all logs with alerts
journal-monitor

# Monitor specific service
journal-monitor -u sshd

# Errors only
journal-monitor -p err
```

## Audit Rules Summary

| Key | Monitored Files/Actions |
|-----|------------------------|
| `sudoers_changes` | `/etc/sudoers`, `/etc/sudoers.d/*` |
| `identity_changes` | `/etc/passwd`, `/etc/group`, `/etc/shadow` |
| `ssh_config_changes` | `/etc/ssh/sshd_config`, `/etc/ssh/ssh_config` |
| `pam_changes` | `/etc/pam.d/*`, `/etc/security/*` |
| `cron_changes` | `/etc/crontab`, `/etc/cron.d/*`, `/var/spool/cron/*` |
| `systemd_changes` | `/etc/systemd/system/*` |
| `privileged_cmd` | useradd, userdel, usermod, passwd, sudo, su |
| `kernel_modules` | Module loading/unloading operations |

## Verification

After running the playbook, verify the setup:

```bash
# Check journald status
systemctl status systemd-journald
journalctl --verify

# Check rsyslog status
systemctl status rsyslog
rsyslogd -N1

# Check auditd status
systemctl status auditd
auditctl -l | head -20

# Test audit rules
ausearch -k sudoers_changes --start today

# Check tools are installed
ls -la /opt/dapmeet/scripts/journal/
```

## Log Locations

| Log Type | Location |
|----------|----------|
| System Journal | `/var/log/journal/` |
| Application Logs | `/var/log/dapmeet/` |
| Security Logs | `/var/log/dapmeet/security.log` |
| Audit Logs | `/var/log/audit/audit.log` |
| Daily Reports | `/var/log/dapmeet/reports/` |

## Troubleshooting

### Journald Issues
```bash
# Check journal disk usage
journalctl --disk-usage

# Verify journal integrity
journalctl --verify

# View journal configuration
systemd-analyze cat-config systemd/journald.conf
```

### Auditd Issues
```bash
# Check audit status
auditctl -s

# List all rules
auditctl -l

# Check for rule errors
augenrules --check

# View audit log
ausearch -m AVC --start today
```

### Common Issues

1. **Journal not persisting**: Ensure `/var/log/journal/` exists with correct permissions
2. **Audit rules not loading**: Check syntax with `auditctl -l` and logs in `/var/log/audit/`
3. **Tools not found**: Ensure symlinks exist in `/usr/local/bin/`

## Key Learning Outcomes

- Systemd-journald configuration for persistent logging
- Rsyslog integration with systemd journal
- Linux Audit System (auditd) for security monitoring
- Custom audit rules for sensitive file monitoring
- Shell scripting for log analysis and monitoring
- Ansible automation for infrastructure configuration

## Repository

This playbook should be stored in GitHub/GitLab as per assignment requirements.

```bash
# Initialize git repository
git init
git add .
git commit -m "SIS6: Journaling and Auditing Setup"
git remote add origin <your-repo-url>
git push -u origin main
```

