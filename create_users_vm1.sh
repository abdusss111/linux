#!/bin/bash
# setup_vm1_frontend.sh
# Script for Frontend VM - Dapmeet project

set -e

echo "=== Dapmeet Frontend VM Setup ==="
echo "Starting setup for VM1 (Frontend Server)..."

# Create groups
echo ""
echo "Step 1: Creating groups..."

sudo groupadd -f www-data
sudo groupadd -f deployer
sudo groupadd -f sysadmin
sudo groupadd -f devops
sudo groupadd -f automation
sudo groupadd -f monitoring
sudo groupadd -f auditor
sudo groupadd -f dapmeet

echo "✓ Groups created"

# Create service accounts
echo ""
echo "Step 2: Creating service accounts..."

sudo useradd -r -s /usr/sbin/nologin -g www-data nginx 2>/dev/null || echo "User nginx already exists"
echo "✓ Created user: nginx"

sudo useradd -m -s /bin/bash -g deployer deployer 2>/dev/null || echo "User deployer already exists"
sudo usermod -aG dapmeet deployer
echo "✓ Created user: deployer"

# Create administrative users
echo ""
echo "Step 3: Creating administrative users..."

sudo useradd -m -s /bin/bash -g sysadmin sysadmin 2>/dev/null || echo "User sysadmin already exists"
sudo usermod -aG sudo sysadmin
echo "✓ Created user: sysadmin"

sudo useradd -m -s /bin/bash -g devops devops_user 2>/dev/null || echo "User devops_user already exists"
sudo usermod -aG dapmeet devops_user
echo "✓ Created user: devops_user"

sudo useradd -m -s /bin/bash -g automation automation 2>/dev/null || echo "User automation already exists"
sudo usermod -aG dapmeet automation
echo "✓ Created user: automation"

sudo useradd -r -s /bin/bash -g monitoring monitoring 2>/dev/null || echo "User monitoring already exists"
echo "✓ Created user: monitoring"

sudo useradd -m -s /bin/bash -g auditor auditor 2>/dev/null || echo "User auditor already exists"
echo "✓ Created user: auditor"

# Verification
echo ""
echo "=== VM1 Frontend Setup Complete ==="
echo "Users created: nginx, deployer, sysadmin, devops_user, automation, monitoring, auditor"
