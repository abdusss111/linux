#!/bin/bash
#==============================================================================
# Main Setup Script for VM1 (Frontend Server)
# Dapmeet Project - Complete Frontend Infrastructure Setup
#
# This script orchestrates the setup of:
#   - SIS2: Users and permissions
#   - SIS3: Packages and firewall
#   - SIS4: Docker, systemd services, and cron jobs
#   - SIS6: Journaling configuration
#
# Usage: sudo bash main.sh [--skip-docker-pull] [--verbose]
#==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/lib.sh"

# Parse arguments
SKIP_DOCKER_PULL=false
VERBOSE=false
for arg in "$@"; do
    case $arg in
        --skip-docker-pull) SKIP_DOCKER_PULL=true ;;
        --verbose) VERBOSE=true; set -x ;;
        --help) 
            echo "Usage: sudo bash $0 [--skip-docker-pull] [--verbose]"
            exit 0
            ;;
    esac
done

# Check root
check_root

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║           DAPMEET VM1 (FRONTEND) SETUP                             ║"
echo "║           Complete Infrastructure Configuration                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

START_TIME=$(date +%s)

#==============================================================================
# STEP 1: System Updates and Base Packages (SIS3)
#==============================================================================
print_section "Step 1: System Updates and Base Packages"

ensure_apt_updated 24

# Install essential packages
PACKAGES=(
    "vim" "curl" "wget" "git" "htop" "net-tools"
    "ca-certificates" "gnupg" "lsb-release"
    "ufw" "fail2ban" "logrotate"
    "nginx" "certbot" "python3-certbot-nginx"
)

for pkg in "${PACKAGES[@]}"; do
    ensure_package "$pkg"
done

log_success "Base packages installed"

#==============================================================================
# STEP 2: Create Groups (SIS2)
#==============================================================================
print_section "Step 2: Creating Groups"

GROUPS=("www-data" "deployer" "sysadmin" "devops" "automation" "monitoring" "auditor" "dapmeet")

for grp in "${GROUPS[@]}"; do
    ensure_group "$grp"
done

log_success "All groups created"

#==============================================================================
# STEP 3: Create Users (SIS2)
#==============================================================================
print_section "Step 3: Creating Users"

# Service accounts
ensure_user "nginx" "www-data" "" "/usr/sbin/nologin" "true"

# Application users
ensure_user "deployer" "deployer" "/home/deployer" "/bin/bash" "false"
ensure_user_in_group "deployer" "dapmeet"

# Administrative users
ensure_user "sysadmin" "sysadmin" "/home/sysadmin" "/bin/bash" "false"
ensure_user_in_group "sysadmin" "sudo"

ensure_user "devops_user" "devops" "/home/devops_user" "/bin/bash" "false"
ensure_user_in_group "devops_user" "dapmeet"

ensure_user "automation" "automation" "/home/automation" "/bin/bash" "false"
ensure_user_in_group "automation" "dapmeet"

ensure_user "monitoring" "monitoring" "" "/bin/bash" "true"

ensure_user "auditor" "auditor" "/home/auditor" "/bin/bash" "false"

log_success "All users created"

#==============================================================================
# STEP 4: Create Directory Structure (SIS2)
#==============================================================================
print_section "Step 4: Creating Directory Structure"

ensure_directory "/opt/dapmeet" "root:dapmeet" "755"
ensure_directory "/opt/dapmeet/frontend" "deployer:dapmeet" "755"
ensure_directory "/opt/dapmeet/scripts" "root:dapmeet" "750"
ensure_directory "/opt/dapmeet/scripts/cron" "root:dapmeet" "750"
ensure_directory "/var/log/dapmeet" "root:dapmeet" "775"
ensure_directory "/var/log/nginx" "www-data:adm" "750"
ensure_directory "/var/backups/dapmeet" "root:dapmeet" "750"
ensure_directory "/var/backups/dapmeet/logs" "root:dapmeet" "750"
ensure_directory "/etc/dapmeet" "root:dapmeet" "755"
ensure_directory "/etc/dapmeet/nginx" "root:devops" "750"
ensure_directory "/etc/dapmeet/ssl" "root:root" "700"

log_success "Directory structure created"

#==============================================================================
# STEP 5: Configure Sudoers (SIS2)
#==============================================================================
print_section "Step 5: Configuring Sudoers"

# DevOps sudoers
ensure_sudoers "devops" "# DevOps group permissions
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl status nginx
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop nginx
%devops ALL=(ALL) NOPASSWD: /usr/sbin/nginx -t"

# Deployer sudoers
ensure_sudoers "deployer" "# Deployer permissions
deployer ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
deployer ALL=(ALL) NOPASSWD: /usr/bin/npm *
deployer ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-frontend
deployer ALL=(ALL) NOPASSWD: /usr/bin/systemctl status dapmeet-frontend"

# Monitoring sudoers
ensure_sudoers "monitoring" "# Monitoring permissions
monitoring ALL=(ALL) NOPASSWD: /usr/bin/systemctl status *
monitoring ALL=(ALL) NOPASSWD: /usr/bin/journalctl *
monitoring ALL=(ALL) NOPASSWD: /usr/bin/docker ps
monitoring ALL=(ALL) NOPASSWD: /usr/bin/docker stats --no-stream"

# Automation sudoers
ensure_sudoers "automation" "# Automation permissions
automation ALL=(ALL) NOPASSWD: /opt/dapmeet/scripts/*.sh
automation ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-*
automation ALL=(ALL) NOPASSWD: /usr/bin/systemctl status dapmeet-*
automation ALL=(ALL) NOPASSWD: /usr/bin/docker *"

log_success "Sudoers configured"

#==============================================================================
# STEP 6: Configure Firewall (SIS3)
#==============================================================================
print_section "Step 6: Configuring Firewall"

# Enable UFW if not enabled
if ! ufw status | grep -q "Status: active"; then
    ufw --force enable
    log_success "UFW enabled"
else
    log_skip "UFW is already enabled"
fi

# Add firewall rules
ensure_ufw_rule "OpenSSH"
ensure_ufw_rule "80/tcp"
ensure_ufw_rule "443/tcp"
ensure_ufw_rule "3000/tcp"

# Set default policies
ufw default deny incoming > /dev/null 2>&1
ufw default allow outgoing > /dev/null 2>&1

log_success "Firewall configured"

#==============================================================================
# STEP 7: Install Docker (SIS4)
#==============================================================================
print_section "Step 7: Installing Docker"

ensure_docker

# Add users to docker group
ensure_user_in_group "deployer" "docker"
ensure_user_in_group "devops_user" "docker"
ensure_user_in_group "automation" "docker"

log_success "Docker configured"

#==============================================================================
# STEP 8: Install Node.js (SIS3)
#==============================================================================
print_section "Step 8: Installing Node.js"

ensure_nodejs 20

log_success "Node.js configured"

#==============================================================================
# STEP 9: Install Systemd Service (SIS4)
#==============================================================================
print_section "Step 9: Installing Systemd Service"

SYSTEMD_SERVICE="/etc/systemd/system/dapmeet-frontend.service"

cat > "$SYSTEMD_SERVICE" << 'EOF'
[Unit]
Description=Dapmeet Frontend Docker Container
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=10
TimeoutStartSec=300

# Pre-start cleanup
ExecStartPre=-/usr/bin/docker stop dapmeet-frontend
ExecStartPre=-/usr/bin/docker rm dapmeet-frontend
ExecStartPre=/usr/bin/docker pull abdusss111/dapmeet-client:latest

# Start container
ExecStart=/usr/bin/docker run --rm --name dapmeet-frontend \
    -p 3000:3000 \
    -e NODE_ENV=production \
    -v /opt/dapmeet/frontend/.env:/app/.env:ro \
    --health-cmd="curl -f http://localhost:3000/health || exit 1" \
    --health-interval=30s \
    --health-timeout=10s \
    --health-retries=3 \
    abdusss111/dapmeet-client:latest

# Stop container gracefully
ExecStop=/usr/bin/docker stop -t 30 dapmeet-frontend

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SYSTEMD_SERVICE"
systemctl daemon-reload

if ! service_is_enabled "dapmeet-frontend"; then
    systemctl enable dapmeet-frontend
    log_success "Enabled dapmeet-frontend service"
else
    log_skip "dapmeet-frontend service already enabled"
fi

log_success "Systemd service installed"

#==============================================================================
# STEP 10: Install Cron Scripts (SIS4)
#==============================================================================
print_section "Step 10: Installing Cron Scripts"

CRON_DIR="/opt/dapmeet/scripts/cron"

# Backup frontend logs script
cat > "$CRON_DIR/backup_frontend_logs.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/backups/dapmeet/logs"
LOG_DIRS=("/var/log/dapmeet" "/var/log/nginx")
DATE=$(date +%Y%m%d)
RETENTION_DAYS=30
LOG_FILE="/var/log/dapmeet/backup.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"; }

mkdir -p "$BACKUP_DIR"
log "Starting frontend logs backup..."

for LOG_DIR in "${LOG_DIRS[@]}"; do
    if [ -d "$LOG_DIR" ]; then
        DIR_NAME=$(basename "$LOG_DIR")
        BACKUP_FILE="$BACKUP_DIR/${DIR_NAME}_logs_$DATE.tar.gz"
        tar -czf "$BACKUP_FILE" -C "$(dirname "$LOG_DIR")" "$DIR_NAME" 2>/dev/null || log "Warning: Some files could not be backed up"
        chmod 640 "$BACKUP_FILE"
        log "Backed up $LOG_DIR"
    fi
done

find "$BACKUP_DIR" -name "*_logs_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
log "Backup completed"
EOF
chmod +x "$CRON_DIR/backup_frontend_logs.sh"

# SSL renewal check script
cat > "$CRON_DIR/check_ssl_renewal.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

CERT_FILE="/etc/dapmeet/ssl/fullchain.pem"
DAYS_WARNING=30
LOG_FILE="/var/log/dapmeet/ssl_check.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"; }

log "Checking SSL certificate..."

if [ ! -f "$CERT_FILE" ]; then
    log "WARNING: Certificate not found at $CERT_FILE"
    # Try certbot renewal anyway
    if command -v certbot &> /dev/null; then
        certbot renew --quiet 2>/dev/null || true
    fi
    exit 0
fi

EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" 2>/dev/null | cut -d= -f2)
if [ -n "$EXPIRY_DATE" ]; then
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$EXPIRY_DATE" +%s 2>/dev/null || echo 0)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
    
    log "Certificate expires in $DAYS_LEFT days"
    
    if [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
        log "WARNING: Certificate expiring soon! Attempting renewal..."
        if command -v certbot &> /dev/null; then
            certbot renew --quiet && log "Renewal successful" || log "Renewal failed"
        fi
    fi
fi
EOF
chmod +x "$CRON_DIR/check_ssl_renewal.sh"

# Configure crontab
CRON_FILE="/etc/cron.d/dapmeet-frontend"
cat > "$CRON_FILE" << 'EOF'
# Dapmeet Frontend Cron Jobs
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Backup frontend logs - Daily at 2:00 AM
0 2 * * * root /opt/dapmeet/scripts/cron/backup_frontend_logs.sh >> /var/log/dapmeet/cron.log 2>&1

# Check SSL certificate renewal - Weekly on Mondays at 6:00 AM
0 6 * * 1 root /opt/dapmeet/scripts/cron/check_ssl_renewal.sh >> /var/log/dapmeet/cron.log 2>&1
EOF
chmod 644 "$CRON_FILE"

log_success "Cron scripts installed"

#==============================================================================
# STEP 11: Configure Journald (SIS6)
#==============================================================================
print_section "Step 11: Configuring Journald"

mkdir -p /etc/systemd/journald.conf.d

cat > /etc/systemd/journald.conf.d/dapmeet.conf << 'EOF'
[Journal]
# Persistent storage
Storage=persistent
Compress=yes
SystemMaxUse=500M
SystemKeepFree=1G
SystemMaxFileSize=50M
MaxRetentionSec=1month
ForwardToSyslog=yes
EOF

systemctl restart systemd-journald 2>/dev/null || true
log_success "Journald configured"

#==============================================================================
# STEP 12: Configure Services (Enable Nginx, Fail2ban)
#==============================================================================
print_section "Step 12: Configuring Services"

ensure_service_running "nginx"
ensure_service_running "fail2ban"
ensure_service_running "cron"

log_success "Services configured"

#==============================================================================
# STEP 13: Pull Docker Image (Optional)
#==============================================================================
print_section "Step 13: Docker Image"

if [ "$SKIP_DOCKER_PULL" = true ]; then
    log_skip "Docker image pull skipped (--skip-docker-pull)"
else
    log_info "Pulling Docker image..."
    if docker pull abdusss111/dapmeet-client:latest 2>/dev/null; then
        log_success "Docker image pulled successfully"
    else
        log_warning "Failed to pull Docker image (will pull on service start)"
    fi
fi

#==============================================================================
# STEP 14: Verification
#==============================================================================
print_section "Step 14: Verification"

echo "Checking installation..."
echo ""

# Check Docker
if command_exists docker && service_is_running docker; then
    echo -e "${GREEN}✓${NC} Docker: $(docker --version | head -1)"
else
    echo -e "${RED}✗${NC} Docker: Not running"
fi

# Check Node.js
if command_exists node; then
    echo -e "${GREEN}✓${NC} Node.js: $(node --version)"
else
    echo -e "${RED}✗${NC} Node.js: Not installed"
fi

# Check Nginx
if service_is_running nginx; then
    echo -e "${GREEN}✓${NC} Nginx: Running"
else
    echo -e "${YELLOW}!${NC} Nginx: Not running"
fi

# Check UFW
if ufw status | grep -q "Status: active"; then
    echo -e "${GREEN}✓${NC} UFW: Active"
else
    echo -e "${RED}✗${NC} UFW: Inactive"
fi

# Check systemd service
if [ -f /etc/systemd/system/dapmeet-frontend.service ]; then
    echo -e "${GREEN}✓${NC} Systemd service: Installed"
else
    echo -e "${RED}✗${NC} Systemd service: Missing"
fi

# Check cron
if [ -f /etc/cron.d/dapmeet-frontend ]; then
    echo -e "${GREEN}✓${NC} Cron jobs: Configured"
else
    echo -e "${RED}✗${NC} Cron jobs: Missing"
fi

#==============================================================================
# Summary
#==============================================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

print_summary "VM1 (FRONTEND) SETUP COMPLETE!"
echo ""
echo "  Duration: ${DURATION} seconds"
echo ""
echo "  Components installed:"
echo "    ✓ Users and groups (SIS2)"
echo "    ✓ Directory structure (SIS2)"
echo "    ✓ Sudoers configuration (SIS2)"
echo "    ✓ Base packages (SIS3)"
echo "    ✓ Firewall rules (SIS3)"
echo "    ✓ Docker (SIS4)"
echo "    ✓ Node.js (SIS3)"
echo "    ✓ Systemd service (SIS4)"
echo "    ✓ Cron jobs (SIS4)"
echo "    ✓ Journald (SIS6)"
echo ""
echo "  Next steps:"
echo "    1. Configure /opt/dapmeet/frontend/.env"
echo "    2. Start the service: sudo systemctl start dapmeet-frontend"
echo "    3. Check status: sudo systemctl status dapmeet-frontend"
echo ""
echo "=============================================="

exit 0

