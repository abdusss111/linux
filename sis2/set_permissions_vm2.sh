#!/bin/bash
# permissions_vm2_backend.sh
# Set up permissions for VM2 Backend & Database Server

set -e

echo "=== Setting up permissions for VM2 (Backend & Database) ==="

# Step 1: Create directory structure
echo ""
echo "Step 1: Creating directory structure..."

sudo mkdir -p /opt/dapmeet/backend
sudo mkdir -p /opt/dapmeet/worker
sudo mkdir -p /opt/dapmeet/scripts
sudo mkdir -p /var/dapmeet/processing
sudo mkdir -p /var/dapmeet/uploads
sudo mkdir -p /var/log/dapmeet
sudo mkdir -p /var/backups/dapmeet/postgresql
sudo mkdir -p /var/backups/dapmeet/logs
sudo mkdir -p /etc/dapmeet/backend
sudo mkdir -p /tmp/dapmeet-setup

echo "✓ Directories created"

# Step 2: Set ownership and permissions for directories
echo ""
echo "Step 2: Setting directory permissions..."

# Backend directories
sudo chown -R dapmeet-backend:dapmeet /opt/dapmeet/backend 2>/dev/null || sudo chown -R root:root /opt/dapmeet/backend
sudo chmod -R 755 /opt/dapmeet/backend

# Worker directories
sudo chown -R dapmeet-worker:dapmeet /opt/dapmeet/worker 2>/dev/null || sudo chown -R root:root /opt/dapmeet/worker
sudo chmod -R 755 /opt/dapmeet/worker

# Scripts directory
sudo chown -R root:dapmeet /opt/dapmeet/scripts 2>/dev/null || sudo chown -R root:root /opt/dapmeet/scripts
sudo chmod -R 750 /opt/dapmeet/scripts

# Data directories
sudo chown -R dapmeet-backend:dapmeet /var/dapmeet 2>/dev/null || sudo chown -R root:root /var/dapmeet
sudo chmod -R 775 /var/dapmeet/processing
sudo chmod -R 775 /var/dapmeet/uploads

# Application logs
sudo chown -R root:dapmeet /var/log/dapmeet 2>/dev/null || sudo chown -R root:root /var/log/dapmeet
sudo chmod -R 775 /var/log/dapmeet

# Backup directories
sudo chown -R backup:postgres /var/backups/dapmeet/postgresql 2>/dev/null || sudo chown -R root:root /var/backups/dapmeet/postgresql
sudo chmod 750 /var/backups/dapmeet/postgresql

sudo chown -R root:dapmeet /var/backups/dapmeet/logs 2>/dev/null || sudo chown -R root:root /var/backups/dapmeet/logs
sudo chmod 750 /var/backups/dapmeet/logs

# Config directories
sudo chown -R root:dapmeet /etc/dapmeet 2>/dev/null || sudo chown -R root:root /etc/dapmeet
sudo chmod -R 750 /etc/dapmeet

echo "✓ Directory permissions set"

# Step 3: Configure sudoers for devops group
echo ""
echo "Step 3: Configuring sudoers..."

sudo tee /etc/sudoers.d/devops << 'EOF'
# DevOps group permissions for Backend VM
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl status dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/docker *
EOF

sudo chmod 440 /etc/sudoers.d/devops
echo "✓ DevOps sudoers configured"

# Step 4: Configure sudoers for DBA
sudo tee /etc/sudoers.d/dba << 'EOF'
# DBA group permissions
%dba ALL=(postgres) NOPASSWD: /usr/bin/psql
%dba ALL=(postgres) NOPASSWD: /usr/bin/pg_dump
%dba ALL=(postgres) NOPASSWD: /usr/bin/pg_restore
%dba ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart postgresql
%dba ALL=(ALL) NOPASSWD: /usr/bin/systemctl status postgresql
EOF

sudo chmod 440 /etc/sudoers.d/dba
echo "✓ DBA sudoers configured"

# Step 5: Configure sudoers for automation
sudo tee /etc/sudoers.d/automation << 'EOF'
# Automation user permissions
automation ALL=(ALL) NOPASSWD: /opt/dapmeet/scripts/deploy.sh
automation ALL=(ALL) NOPASSWD: /opt/dapmeet/scripts/*.sh
automation ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-*
automation ALL=(dapmeet-backend) NOPASSWD: ALL
automation ALL=(dapmeet-worker) NOPASSWD: ALL
automation ALL=(ALL) NOPASSWD: /usr/bin/docker *
EOF

sudo chmod 440 /etc/sudoers.d/automation
echo "✓ Automation sudoers configured"

# Step 6: Configure sudoers for backup
sudo tee /etc/sudoers.d/backup << 'EOF'
# Backup user permissions
backup ALL=(postgres) NOPASSWD: /usr/bin/pg_dump
backup ALL=(postgres) NOPASSWD: /usr/bin/pg_dumpall
backup ALL=(ALL) NOPASSWD: /usr/bin/tar
backup ALL=(ALL) NOPASSWD: /usr/bin/rsync
EOF

sudo chmod 440 /etc/sudoers.d/backup
echo "✓ Backup sudoers configured"

# Step 7: Configure sudoers for monitoring
sudo tee /etc/sudoers.d/monitoring << 'EOF'
# Monitoring permissions
monitoring ALL=(ALL) NOPASSWD: /usr/bin/systemctl status *
monitoring ALL=(ALL) NOPASSWD: /usr/bin/journalctl *
monitoring ALL=(postgres) NOPASSWD: /usr/bin/psql -c "SELECT *"
monitoring ALL=(ALL) NOPASSWD: /usr/bin/docker ps
monitoring ALL=(ALL) NOPASSWD: /usr/bin/docker stats --no-stream
EOF

sudo chmod 440 /etc/sudoers.d/monitoring
echo "✓ Monitoring sudoers configured"

# Verification
echo ""
echo "Step 8: Verification..."
echo ""
echo "Directory permissions:"
ls -la /opt/dapmeet/
ls -la /var/dapmeet/
ls -la /var/log/dapmeet/
ls -la /var/backups/dapmeet/
ls -la /etc/dapmeet/

echo ""
echo "Sudoers files:"
ls -l /etc/sudoers.d/

echo ""
echo "=== VM2 Permissions Setup Complete ==="

