#!/bin/bash
#==============================================================================
# Script: setup_vm2.sh
# Purpose: Setup Docker, systemd service, and cron jobs for VM2 (Backend)
# Usage: sudo bash setup_vm2.sh
#==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root: sudo bash $0"
    exit 1
fi

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="/etc/systemd/system"
CRON_SCRIPTS_DIR="/opt/dapmeet/scripts/cron"
LOG_DIR="/var/log/dapmeet"
BACKUP_DIR="/var/backups/dapmeet"
DATA_DIR="/var/dapmeet"

log_info "Starting VM2 (Backend) SIS4 setup..."
log_info "Script directory: $SCRIPT_DIR"

#==============================================================================
# Step 1: Install Docker (if not already installed)
#==============================================================================
log_info "Step 1: Checking Docker installation..."

if command -v docker &> /dev/null; then
    log_success "Docker is already installed: $(docker --version)"
else
    log_info "Installing Docker..."
    
    # Install prerequisites
    apt-get update
    apt-get install -y ca-certificates curl gnupg lsb-release
    
    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    
    # Set up Docker repository (detect OS)
    OS_ID=$(. /etc/os-release && echo "$ID")
    VERSION_CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
    
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${OS_ID} ${VERSION_CODENAME} stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    log_success "Docker installed successfully"
fi

# Verify Docker is running
if systemctl is-active --quiet docker; then
    log_success "Docker service is running"
else
    log_error "Docker service is not running"
    systemctl start docker
fi

#==============================================================================
# Step 2: Create required directories
#==============================================================================
log_info "Step 2: Creating required directories..."

mkdir -p "$LOG_DIR"
mkdir -p "$BACKUP_DIR/postgresql"
mkdir -p "$BACKUP_DIR/logs"
mkdir -p "$CRON_SCRIPTS_DIR"
mkdir -p "$DATA_DIR/processing"
mkdir -p "$DATA_DIR/uploads"
mkdir -p /opt/dapmeet/backend
mkdir -p /etc/dapmeet/backend
mkdir -p /tmp/dapmeet-setup

# Set permissions
chown -R root:dapmeet "$LOG_DIR" 2>/dev/null || chown -R root:root "$LOG_DIR"
chmod 775 "$LOG_DIR"

# Processing directory needs specific permissions
chown -R root:dapmeet "$DATA_DIR" 2>/dev/null || chown -R root:root "$DATA_DIR"
chmod 775 "$DATA_DIR/processing"

# Backup directory permissions for backup user
chown -R backup:postgres "$BACKUP_DIR/postgresql" 2>/dev/null || chown -R root:root "$BACKUP_DIR/postgresql"
chmod 750 "$BACKUP_DIR/postgresql"

log_success "Directories created"

#==============================================================================
# Step 3: Install systemd service
#==============================================================================
log_info "Step 3: Installing systemd service for dapmeet-backend..."

# Copy systemd service file
cp "$SCRIPT_DIR/systemd/dapmeet-backend.service" "$SYSTEMD_DIR/"
chmod 644 "$SYSTEMD_DIR/dapmeet-backend.service"

# Reload systemd daemon
systemctl daemon-reload

# Enable service (but don't start yet - user might want to configure first)
systemctl enable dapmeet-backend.service

log_success "Systemd service installed and enabled"

#==============================================================================
# Step 4: Install cron scripts
#==============================================================================
log_info "Step 4: Installing cron scripts..."

# Copy cron scripts
cp "$SCRIPT_DIR/cron/backend/backup_postgres.sh" "$CRON_SCRIPTS_DIR/"
cp "$SCRIPT_DIR/cron/backend/cleanup_processing.sh" "$CRON_SCRIPTS_DIR/"
cp "$SCRIPT_DIR/cron/backend/rotate_backend_logs.sh" "$CRON_SCRIPTS_DIR/"

# Make scripts executable
chmod +x "$CRON_SCRIPTS_DIR"/*.sh

log_success "Cron scripts installed to $CRON_SCRIPTS_DIR"

#==============================================================================
# Step 5: Configure crontab
#==============================================================================
log_info "Step 5: Configuring crontab..."

# Create crontab entries
CRON_FILE="/etc/cron.d/dapmeet-backend"

cat > "$CRON_FILE" << 'EOF'
# Dapmeet Backend Cron Jobs
# Generated by setup_vm2.sh

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# PostgreSQL backup - Daily at 3:00 AM
0 3 * * * root /opt/dapmeet/scripts/cron/backup_postgres.sh >> /var/log/dapmeet/cron.log 2>&1

# Cleanup old processing files - Daily at 4:30 AM
30 4 * * * root /opt/dapmeet/scripts/cron/cleanup_processing.sh >> /var/log/dapmeet/cron.log 2>&1

# Rotate backend logs - Weekly on Sundays at 5:00 AM
0 5 * * 0 root /opt/dapmeet/scripts/cron/rotate_backend_logs.sh >> /var/log/dapmeet/cron.log 2>&1
EOF

chmod 644 "$CRON_FILE"

log_success "Crontab configured"

#==============================================================================
# Step 6: Pull Docker image
#==============================================================================
log_info "Step 6: Pulling Docker image..."

if docker pull abdusss111/dapmeet-service:latest; then
    log_success "Docker image pulled successfully"
else
    log_warning "Failed to pull Docker image. Service will pull on first start."
fi

#==============================================================================
# Step 7: Install logrotate (for log rotation script)
#==============================================================================
log_info "Step 7: Ensuring logrotate is installed..."

if command -v logrotate &> /dev/null; then
    log_success "Logrotate is already installed"
else
    apt-get install -y logrotate
    log_success "Logrotate installed"
fi

#==============================================================================
# Summary
#==============================================================================
echo ""
echo "=============================================="
echo -e "${GREEN}VM2 (Backend) SIS4 Setup Complete!${NC}"
echo "=============================================="
echo ""
echo "Installed components:"
echo "  ✓ Docker"
echo "  ✓ Systemd service: dapmeet-backend.service"
echo "  ✓ Cron scripts:"
echo "    - backup_postgres.sh (Daily 3:00 AM)"
echo "    - cleanup_processing.sh (Daily 4:30 AM)"
echo "    - rotate_backend_logs.sh (Weekly Sun 5:00 AM)"
echo ""
echo "Important: Before starting the service, ensure:"
echo "  1. PostgreSQL is running and configured"
echo "  2. Database 'dapmeet' exists"
echo "  3. Update DATABASE_URL in the service file if needed"
echo ""
echo "To start the backend service:"
echo "  sudo systemctl start dapmeet-backend"
echo ""
echo "To check service status:"
echo "  sudo systemctl status dapmeet-backend"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u dapmeet-backend -f"
echo "  sudo docker logs dapmeet-backend"
echo ""
echo "=============================================="

exit 0


