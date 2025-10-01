#!/bin/bash
# permissions_vm1_frontend.sh
# Set up permissions for VM1 Frontend Server

set -e

echo "=== Setting up permissions for VM1 (Frontend) ==="

# Step 1: Create directory structure
echo ""
echo "Step 1: Creating directory structure..."

sudo mkdir -p /opt/dapmeet/frontend
sudo mkdir -p /opt/dapmeet/scripts
sudo mkdir -p /var/log/dapmeet
sudo mkdir -p /var/log/nginx
sudo mkdir -p /etc/dapmeet/nginx
sudo mkdir -p /etc/dapmeet/ssl

echo "✓ Directories created"

# Step 2: Set ownership and permissions for directories
echo ""
echo "Step 2: Setting directory permissions..."

# Frontend directory
sudo chown -R deployer:dapmeet /opt/dapmeet/frontend
sudo chmod -R 755 /opt/dapmeet/frontend

# Scripts directory
sudo chown -R root:dapmeet /opt/dapmeet/scripts
sudo chmod -R 750 /opt/dapmeet/scripts

# Nginx directories
sudo chown -R nginx:www-data /var/log/nginx
sudo chmod -R 640 /var/log/nginx
sudo chown -R root:devops /etc/dapmeet/nginx
sudo chmod -R 750 /etc/dapmeet/nginx

# Application logs
sudo chown -R root:dapmeet /var/log/dapmeet
sudo chmod -R 755 /var/log/dapmeet

echo "✓ Directory permissions set"

# Step 3: Configure sudoers for devops group
echo ""
echo "Step 3: Configuring sudoers..."

sudo tee /etc/sudoers.d/devops << 'EOF'
# DevOps group permissions
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl status nginx
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop nginx
%devops ALL=(ALL) /usr/sbin/nginx -t
EOF

sudo chmod 440 /etc/sudoers.d/devops
echo "✓ DevOps sudoers configured"

# Step 4: Configure sudoers for deployer
sudo tee /etc/sudoers.d/deployer << 'EOF'
# Deployer permissions
deployer ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
deployer ALL=(ALL) NOPASSWD: /usr/bin/npm *
EOF

sudo chmod 440 /etc/sudoers.d/deployer
echo "✓ Deployer sudoers configured"

# Step 5: Configure sudoers for monitoring
sudo tee /etc/sudoers.d/monitoring << 'EOF'
# Monitoring permissions
monitoring ALL=(ALL) NOPASSWD: /usr/bin/systemctl status *
monitoring ALL=(ALL) NOPASSWD: /usr/bin/journalctl *
EOF

sudo chmod 440 /etc/sudoers.d/monitoring
echo "✓ Monitoring sudoers configured"

# Verification
echo ""
echo "Step 4: Verification..."
echo ""
echo "Directory permissions:"
ls -la /opt/dapmeet/
ls -la /var/log/dapmeet/
ls -la /etc/dapmeet/

echo ""
echo "Sudoers files:"
ls -l /etc/sudoers.d/

echo ""
echo "=== VM1 Permissions Setup Complete ==="
