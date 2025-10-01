#!/bin/bash
# permissions_vm2_backend.sh
# Set up permissions for VM2 Backend & Database Server

set -e

echo "=== Setting up permissions for VM2 (Backend & Database) ==="

# Step 1: Create directory structure
echo ""
echo "Step 1: Creating directory structure..."

sudo mkdir -p /opt/dapmeet/backend
sudo mkdir -p /opt/dapmeet/scripts
sudo mkdir -p /var/dapmeet/processing
sudo mkdir -p /var/log/dapmeet
sudo mkdir -p /var/backups/dapmeet/postgresql
sudo mkdir -p /etc/dapmeet/backend

echo "✓ Directories created"

# Step 2: Set ownership and permissions
echo ""
echo "Step 2: Setting directory permissions..."

# Backend directory
sudo chown -R dapmeet-backend:dapmeet /opt/dapmeet/backend
sudo chmod -R 750 /opt/dapmeet/backend

# Create .env file with restricted permissions
sudo touch /opt/dapmeet/backend/.env
sudo chown dapmeet-backend:dapmeet /opt/dapmeet/backend/.env
sudo chmod 600 /opt/dapmeet/backend/.env

# Processing directory
sudo chown -R dapmeet-worker:dapmeet /var/dapmeet/processing
sudo chmod -R 770 /var/dapmeet/processing

# Scripts directory
sudo chown -R root:dapmeet /opt/dapmeet/scripts
sudo chmod -R 750 /opt/dapmeet/scripts

# Logs
sudo mkdir -p /var/log/dapmeet
sudo touch /var/log/dapmeet/backend.log
sudo touch /var/log/dapmeet/worker.log
sudo chown dapmeet-backend:dapmeet /var/log/dapmeet/backend.log
sudo chown dapmeet-worker:dapmeet /var/log/dapmeet/worker.log
sudo chmod 640 /var/log/dapmeet/*.log

# PostgreSQL backup directory
sudo chown -R backup:postgres /var/backups/dapmeet/postgresql
sudo chmod -R 750 /var/backups/dapmeet/postgresql

# Config directory
sudo chown -R root:dapmeet /etc/dapmeet/backend
sudo chmod -R 750 /etc/dapmeet/backend

echo "✓ Directory permissions set"

# Step 3: Configure sudoers for devops
echo ""
echo "Step 3: Configuring sudoers..."

sudo tee /etc/sudoers.d/devops << 'EOF'
# DevOps group permissions
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl status dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl start dapmeet-*
EOF

sudo chmod 440 /etc/sudoers.d/devops
echo "✓ DevOps sudoers configured"

# Step 4: Configure sudoers for DBA
sudo tee /etc/sudoers.d/dba << 'EOF'
# DBA permissions
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
# Automation permissions
automation ALL=(ALL) NOPASSWD: /opt/dapmeet/scripts/deploy.sh
automation ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-*
automation ALL=(dapmeet-backend) NOPASSWD: ALL
automation ALL=(dapmeet-worker) NOPASSWD: ALL
EOF

sudo chmod 440 /etc/sudoers.d/automation
echo "✓ Automation sudoers configured"

# Step 6: Configure sudoers for backup
sudo tee /etc/sudoers.d/backup << 'EOF'
# Backup permissions
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

echo ""
echo "Sudoers files:"
ls -l /etc/sudoers.d/

echo ""
echo "=== VM2 Permissions Setup Complete ==="
