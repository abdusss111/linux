#!/bin/bash
#==============================================================================
# Main Setup Script for VM2 (Backend Server)
# Dapmeet Project - Complete Backend Infrastructure Setup
#
# This script orchestrates the setup of:
#   - SIS2: Users and permissions
#   - SIS3: Packages and firewall
#   - SIS4: Docker, PostgreSQL, systemd services, and cron jobs
#   - SIS6: Journaling configuration
#
# Usage: sudo bash main.sh [--skip-docker-pull] [--skip-db-setup] [--verbose]
#==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common/lib.sh"

# Configuration
DB_NAME="dapmeet"
DB_USER="dapmeet"
DB_PASS="${DAPMEET_DB_PASSWORD:-dapmeet_secure_password}"

# Parse arguments
SKIP_DOCKER_PULL=false
SKIP_DB_SETUP=false
VERBOSE=false
for arg in "$@"; do
    case $arg in
        --skip-docker-pull) SKIP_DOCKER_PULL=true ;;
        --skip-db-setup) SKIP_DB_SETUP=true ;;
        --verbose) VERBOSE=true; set -x ;;
        --help) 
            echo "Usage: sudo bash $0 [--skip-docker-pull] [--skip-db-setup] [--verbose]"
            echo ""
            echo "Environment variables:"
            echo "  DAPMEET_DB_PASSWORD - Database password (default: dapmeet_secure_password)"
            exit 0
            ;;
    esac
done

# Check root
check_root

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║           DAPMEET VM2 (BACKEND) SETUP                              ║"
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
    "python3" "python3-pip" "python3-venv"
)

for pkg in "${PACKAGES[@]}"; do
    ensure_package "$pkg"
done

log_success "Base packages installed"

#==============================================================================
# STEP 2: Create Groups (SIS2)
#==============================================================================
print_section "Step 2: Creating Groups"

GROUPS=("postgres" "dapmeet" "dba" "backup" "sysadmin" "devops" "automation" "monitoring" "auditor")

for grp in "${GROUPS[@]}"; do
    ensure_group "$grp"
done

log_success "All groups created"

#==============================================================================
# STEP 3: Create Users (SIS2)
#==============================================================================
print_section "Step 3: Creating Users"

# PostgreSQL user (will be created by PostgreSQL installation, but ensure group membership)
# ensure_user "postgres" "postgres" "/var/lib/postgresql" "/bin/bash" "true"

# Service accounts
ensure_user "dapmeet-backend" "dapmeet" "/opt/dapmeet/backend" "/bin/bash" "true"
ensure_user "dapmeet-worker" "dapmeet" "/opt/dapmeet/worker" "/bin/bash" "true"

# Administrative users
ensure_user "sysadmin" "sysadmin" "/home/sysadmin" "/bin/bash" "false"
ensure_user_in_group "sysadmin" "sudo"

ensure_user "devops_user" "devops" "/home/devops_user" "/bin/bash" "false"
ensure_user_in_group "devops_user" "dapmeet"
ensure_user_in_group "devops_user" "docker" 2>/dev/null || true

ensure_user "dba_user" "dba" "/home/dba_user" "/bin/bash" "false"
ensure_user_in_group "dba_user" "postgres"

ensure_user "automation" "automation" "/home/automation" "/bin/bash" "false"
ensure_user_in_group "automation" "dapmeet"

ensure_user "monitoring" "monitoring" "" "/bin/bash" "true"

ensure_user "backup" "backup" "" "/bin/bash" "true"
ensure_user_in_group "backup" "postgres"

ensure_user "auditor" "auditor" "/home/auditor" "/bin/bash" "false"

log_success "All users created"

#==============================================================================
# STEP 4: Create Directory Structure (SIS2)
#==============================================================================
print_section "Step 4: Creating Directory Structure"

ensure_directory "/opt/dapmeet" "root:dapmeet" "755"
ensure_directory "/opt/dapmeet/backend" "dapmeet-backend:dapmeet" "755"
ensure_directory "/opt/dapmeet/worker" "dapmeet-worker:dapmeet" "755"
ensure_directory "/opt/dapmeet/scripts" "root:dapmeet" "750"
ensure_directory "/opt/dapmeet/scripts/cron" "root:dapmeet" "750"
ensure_directory "/var/dapmeet" "root:dapmeet" "755"
ensure_directory "/var/dapmeet/processing" "dapmeet-backend:dapmeet" "775"
ensure_directory "/var/dapmeet/uploads" "dapmeet-backend:dapmeet" "775"
ensure_directory "/var/log/dapmeet" "root:dapmeet" "775"
ensure_directory "/var/backups/dapmeet" "root:dapmeet" "750"
ensure_directory "/var/backups/dapmeet/postgresql" "backup:postgres" "750"
ensure_directory "/var/backups/dapmeet/logs" "root:dapmeet" "750"
ensure_directory "/etc/dapmeet" "root:dapmeet" "755"
ensure_directory "/etc/dapmeet/backend" "root:dapmeet" "750"
ensure_directory "/tmp/dapmeet-setup" "root:dapmeet" "755"

log_success "Directory structure created"

#==============================================================================
# STEP 5: Configure Sudoers (SIS2)
#==============================================================================
print_section "Step 5: Configuring Sudoers"

# DevOps sudoers
ensure_sudoers "devops" "# DevOps group permissions
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl status dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/docker *"

# DBA sudoers
ensure_sudoers "dba" "# DBA group permissions
%dba ALL=(postgres) NOPASSWD: /usr/bin/psql
%dba ALL=(postgres) NOPASSWD: /usr/bin/pg_dump
%dba ALL=(postgres) NOPASSWD: /usr/bin/pg_restore
%dba ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart postgresql
%dba ALL=(ALL) NOPASSWD: /usr/bin/systemctl status postgresql"

# Backup sudoers
ensure_sudoers "backup" "# Backup user permissions
backup ALL=(postgres) NOPASSWD: /usr/bin/pg_dump
backup ALL=(postgres) NOPASSWD: /usr/bin/pg_dumpall
backup ALL=(ALL) NOPASSWD: /usr/bin/tar
backup ALL=(ALL) NOPASSWD: /usr/bin/rsync"

# Monitoring sudoers
ensure_sudoers "monitoring" "# Monitoring permissions
monitoring ALL=(ALL) NOPASSWD: /usr/bin/systemctl status *
monitoring ALL=(ALL) NOPASSWD: /usr/bin/journalctl *
monitoring ALL=(ALL) NOPASSWD: /usr/bin/docker ps
monitoring ALL=(ALL) NOPASSWD: /usr/bin/docker stats --no-stream
monitoring ALL=(postgres) NOPASSWD: /usr/bin/psql -c SELECT *"

# Automation sudoers
ensure_sudoers "automation" "# Automation permissions
automation ALL=(ALL) NOPASSWD: /opt/dapmeet/scripts/*.sh
automation ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-*
automation ALL=(ALL) NOPASSWD: /usr/bin/systemctl status dapmeet-*
automation ALL=(dapmeet-backend) NOPASSWD: ALL
automation ALL=(dapmeet-worker) NOPASSWD: ALL
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
ensure_ufw_rule "8000/tcp"   # FastAPI
ensure_ufw_rule "5432/tcp"   # PostgreSQL (consider restricting to specific IPs)

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
ensure_user_in_group "devops_user" "docker"
ensure_user_in_group "automation" "docker"

log_success "Docker configured"

#==============================================================================
# STEP 8: Install PostgreSQL (SIS4)
#==============================================================================
print_section "Step 8: Installing PostgreSQL"

ensure_postgresql

if [ "$SKIP_DB_SETUP" = false ]; then
    ensure_pg_database "$DB_NAME" "$DB_USER" "$DB_PASS"
    
    # Configure PostgreSQL to allow connections from Docker
    PG_HBA="/etc/postgresql/*/main/pg_hba.conf"
    POSTGRESQL_CONF="/etc/postgresql/*/main/postgresql.conf"
    
    # Allow local Docker connections
    if ! grep -q "host.*dapmeet.*172.17" $PG_HBA 2>/dev/null; then
        echo "# Docker network connections" >> $(ls $PG_HBA 2>/dev/null | head -1) 2>/dev/null || true
        echo "host    dapmeet    dapmeet    172.17.0.0/16    md5" >> $(ls $PG_HBA 2>/dev/null | head -1) 2>/dev/null || true
        log_info "Added Docker network to pg_hba.conf"
    fi
    
    # Listen on all interfaces (for Docker)
    if ! grep -q "^listen_addresses = '\*'" $(ls $POSTGRESQL_CONF 2>/dev/null | head -1) 2>/dev/null; then
        sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" $(ls $POSTGRESQL_CONF 2>/dev/null | head -1) 2>/dev/null || true
        log_info "Updated PostgreSQL listen_addresses"
    fi
    
    systemctl restart postgresql 2>/dev/null || true
fi

log_success "PostgreSQL configured"

#==============================================================================
# STEP 9: Install Systemd Service (SIS4)
#==============================================================================
print_section "Step 9: Installing Systemd Service"

SYSTEMD_SERVICE="/etc/systemd/system/dapmeet-backend.service"

cat > "$SYSTEMD_SERVICE" << 'EOF'
[Unit]
Description=Dapmeet Backend Docker Container
Requires=docker.service
After=docker.service network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=10
TimeoutStartSec=300

# Pre-start cleanup
ExecStartPre=-/usr/bin/docker stop dapmeet-backend
ExecStartPre=-/usr/bin/docker rm dapmeet-backend
ExecStartPre=/usr/bin/docker pull abdusss111/dapmeet-service:latest

# Start container with environment configuration
ExecStart=/usr/bin/docker run --rm --name dapmeet-backend \
    -p 8000:8000 \
    -e PYTHONUNBUFFERED=1 \
    -e DATABASE_URL=postgresql://dapmeet:dapmeet_secure_password@host.docker.internal:5432/dapmeet \
    -v /var/dapmeet/processing:/app/processing \
    -v /var/log/dapmeet:/app/logs \
    --add-host=host.docker.internal:host-gateway \
    --health-cmd="curl -f http://localhost:8000/health || exit 1" \
    --health-interval=30s \
    --health-timeout=10s \
    --health-retries=3 \
    abdusss111/dapmeet-service:latest

# Stop container gracefully
ExecStop=/usr/bin/docker stop -t 30 dapmeet-backend

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SYSTEMD_SERVICE"
systemctl daemon-reload

if ! service_is_enabled "dapmeet-backend"; then
    systemctl enable dapmeet-backend
    log_success "Enabled dapmeet-backend service"
else
    log_skip "dapmeet-backend service already enabled"
fi

log_success "Systemd service installed"

#==============================================================================
# STEP 10: Install Cron Scripts (SIS4)
#==============================================================================
print_section "Step 10: Installing Cron Scripts"

CRON_DIR="/opt/dapmeet/scripts/cron"

# PostgreSQL backup script
cat > "$CRON_DIR/backup_postgres.sh" << 'SCRIPT'
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/backups/dapmeet/postgresql"
DB_NAME="dapmeet"
DB_USER="postgres"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_$DATE.sql.gz"
RETENTION_DAYS=7
LOG_FILE="/var/log/dapmeet/postgres_backup.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"; }

handle_error() {
    log "ERROR: Backup failed at line $1"
    [ -f "$BACKUP_FILE" ] && rm -f "$BACKUP_FILE"
    exit 1
}
trap 'handle_error $LINENO' ERR

mkdir -p "$BACKUP_DIR"

log "Starting PostgreSQL backup for: $DB_NAME"

if ! systemctl is-active --quiet postgresql; then
    log "ERROR: PostgreSQL is not running"
    exit 1
fi

if ! sudo -u $DB_USER psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    log "WARNING: Database $DB_NAME does not exist, skipping backup"
    exit 0
fi

sudo -u $DB_USER pg_dump --format=plain --verbose --no-owner --no-privileges "$DB_NAME" 2>> "$LOG_FILE" | gzip > "$BACKUP_FILE"

if [ ! -s "$BACKUP_FILE" ]; then
    log "ERROR: Backup file is empty"
    exit 1
fi

chmod 640 "$BACKUP_FILE"
chown backup:postgres "$BACKUP_FILE" 2>/dev/null || true

log "Backup completed: $BACKUP_FILE"

find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
log "Cleanup completed"
SCRIPT
chmod +x "$CRON_DIR/backup_postgres.sh"

# Cleanup processing files script
cat > "$CRON_DIR/cleanup_processing.sh" << 'SCRIPT'
#!/bin/bash
set -euo pipefail

PROCESSING_DIR="/var/dapmeet/processing"
UPLOAD_DIR="/var/dapmeet/uploads"
DAYS_OLD=3
LOG_FILE="/var/log/dapmeet/cleanup.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"; }

log "Starting processing cleanup..."

cleanup_dir() {
    local dir=$1
    local days=$2
    
    if [ ! -d "$dir" ]; then
        log "Directory $dir does not exist, skipping"
        return
    fi
    
    local count=$(find "$dir" -type f -mtime +$days -delete -print 2>/dev/null | wc -l)
    find "$dir" -type d -empty -delete 2>/dev/null || true
    log "Cleaned $dir: removed $count files"
}

cleanup_dir "$PROCESSING_DIR" $DAYS_OLD
cleanup_dir "$UPLOAD_DIR" 7
cleanup_dir "/tmp/dapmeet-setup" 1

log "Cleanup completed"
SCRIPT
chmod +x "$CRON_DIR/cleanup_processing.sh"

# Log rotation script
cat > "$CRON_DIR/rotate_backend_logs.sh" << 'SCRIPT'
#!/bin/bash
set -euo pipefail

LOG_DIR="/var/log/dapmeet"
STATUS_LOG="$LOG_DIR/rotation_status.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$TIMESTAMP] $1" | tee -a "$STATUS_LOG"; }

log "Starting backend logs rotation..."

mkdir -p "$LOG_DIR"

LOGROTATE_CONF="/tmp/dapmeet-logrotate-$$.conf"

cat > "$LOGROTATE_CONF" << EOF
$LOG_DIR/*.log {
    size 100M
    rotate 5
    compress
    delaycompress
    missingok
    notifempty
    create 640 root dapmeet
}
EOF

/usr/sbin/logrotate -v -f "$LOGROTATE_CONF" >> "$STATUS_LOG" 2>&1 || log "WARNING: Logrotate had issues"
rm -f "$LOGROTATE_CONF"

find "$LOG_DIR" -name "*.log.[0-9]*" ! -name "*.gz" -exec gzip {} \; 2>/dev/null || true

log "Log rotation completed"
SCRIPT
chmod +x "$CRON_DIR/rotate_backend_logs.sh"

# Configure crontab
CRON_FILE="/etc/cron.d/dapmeet-backend"
cat > "$CRON_FILE" << 'EOF'
# Dapmeet Backend Cron Jobs
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
SystemMaxUse=1G
SystemKeepFree=1G
SystemMaxFileSize=100M
MaxRetentionSec=1month
ForwardToSyslog=yes
EOF

systemctl restart systemd-journald 2>/dev/null || true
log_success "Journald configured"

#==============================================================================
# STEP 12: Configure Services
#==============================================================================
print_section "Step 12: Configuring Services"

ensure_service_running "postgresql"
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
    if docker pull abdusss111/dapmeet-service:latest 2>/dev/null; then
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

# Check PostgreSQL
if service_is_running postgresql; then
    PG_VERSION=$(psql --version 2>/dev/null | head -1 || echo "unknown")
    echo -e "${GREEN}✓${NC} PostgreSQL: $PG_VERSION"
else
    echo -e "${RED}✗${NC} PostgreSQL: Not running"
fi

# Check database
if sudo -u postgres psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo -e "${GREEN}✓${NC} Database: $DB_NAME exists"
else
    echo -e "${YELLOW}!${NC} Database: $DB_NAME not found"
fi

# Check UFW
if ufw status | grep -q "Status: active"; then
    echo -e "${GREEN}✓${NC} UFW: Active"
else
    echo -e "${RED}✗${NC} UFW: Inactive"
fi

# Check systemd service
if [ -f /etc/systemd/system/dapmeet-backend.service ]; then
    echo -e "${GREEN}✓${NC} Systemd service: Installed"
else
    echo -e "${RED}✗${NC} Systemd service: Missing"
fi

# Check cron
if [ -f /etc/cron.d/dapmeet-backend ]; then
    echo -e "${GREEN}✓${NC} Cron jobs: Configured"
else
    echo -e "${RED}✗${NC} Cron jobs: Missing"
fi

# Check cron scripts
for script in backup_postgres.sh cleanup_processing.sh rotate_backend_logs.sh; do
    if [ -x "$CRON_DIR/$script" ]; then
        echo -e "${GREEN}✓${NC} Cron script: $script"
    else
        echo -e "${RED}✗${NC} Cron script: $script missing or not executable"
    fi
done

#==============================================================================
# Summary
#==============================================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

print_summary "VM2 (BACKEND) SETUP COMPLETE!"
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
echo "    ✓ PostgreSQL (SIS4)"
echo "    ✓ Systemd service (SIS4)"
echo "    ✓ Cron jobs (SIS4)"
echo "    ✓ Journald (SIS6)"
echo ""
echo "  Database credentials:"
echo "    Database: $DB_NAME"
echo "    User: $DB_USER"
echo "    Password: [set via DAPMEET_DB_PASSWORD or use default]"
echo ""
echo "  Next steps:"
echo "    1. Update DATABASE_URL in systemd service if needed"
echo "    2. Start the service: sudo systemctl start dapmeet-backend"
echo "    3. Check status: sudo systemctl status dapmeet-backend"
echo ""
echo "=============================================="

exit 0

