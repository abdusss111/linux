#!/bin/bash
# setup_vm2_backend.sh
# Script for Backend & Database VM - Dapmeet project

set -e

echo "=== Dapmeet Backend & Database VM Setup ==="
echo "Starting setup for VM2 (Backend Server)..."

# Create groups
echo ""
echo "Step 1: Creating groups..."

sudo groupadd -f postgres
sudo groupadd -f dapmeet
sudo groupadd -f dba
sudo groupadd -f backup
sudo groupadd -f sysadmin
sudo groupadd -f devops
sudo groupadd -f automation
sudo groupadd -f monitoring
sudo groupadd -f auditor

echo "✓ Groups created"

# Create service accounts
echo ""
echo "Step 2: Creating service accounts..."

sudo useradd -r -s /bin/bash -g postgres -d /var/lib/postgresql postgres 2>/dev/null || echo "User postgres already exists"
echo "✓ Created user: postgres"

sudo useradd -r -s /bin/bash -g dapmeet -d /opt/dapmeet/backend dapmeet-backend 2>/dev/null || echo "User dapmeet-backend already exists"
echo "✓ Created user: dapmeet-backend"

sudo useradd -r -s /bin/bash -g dapmeet -d /opt/dapmeet/worker dapmeet-worker 2>/dev/null || echo "User dapmeet-worker already exists"
echo "✓ Created user: dapmeet-worker"

# Create administrative users
echo ""
echo "Step 3: Creating administrative users..."

sudo useradd -m -s /bin/bash -g sysadmin sysadmin 2>/dev/null || echo "User sysadmin already exists"
sudo usermod -aG sudo sysadmin
echo "✓ Created user: sysadmin"

sudo useradd -m -s /bin/bash -g devops devops_user 2>/dev/null || echo "User devops_user already exists"
sudo usermod -aG dapmeet devops_user
echo "✓ Created user: devops_user"

sudo useradd -m -s /bin/bash -g dba dba_user 2>/dev/null || echo "User dba_user already exists"
sudo usermod -aG postgres dba_user
echo "✓ Created user: dba_user"

sudo useradd -m -s /bin/bash -g automation automation 2>/dev/null || echo "User automation already exists"
sudo usermod -aG dapmeet automation
echo "✓ Created user: automation"

sudo useradd -r -s /bin/bash -g monitoring monitoring 2>/dev/null || echo "User monitoring already exists"
echo "✓ Created user: monitoring"

sudo useradd -r -s /bin/bash -g backup backup 2>/dev/null || echo "User backup already exists"
sudo usermod -aG postgres backup
echo "✓ Created user: backup"

sudo useradd -m -s /bin/bash -g auditor auditor 2>/dev/null || echo "User auditor already exists"
echo "✓ Created user: auditor"

# Verification
echo ""
echo "=== VM2 Backend & Database Setup Complete ==="
echo "Users created: postgres, dapmeet-backend, dapmeet-worker, sysadmin, devops_user, dba_user, automation, monitoring, backup, auditor"
