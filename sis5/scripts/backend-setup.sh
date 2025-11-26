#!/bin/bash
#===============================================================================
# Dapmeet Backend VM Setup Script
# SIS1 → SIS5 Complete Implementation
# 
# Student: Abdurakhimov Abdussalam
# VM: Backend (VM2)
# Run as: sudo bash ./backend-setup.sh
#===============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[ℹ]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
section() { echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BLUE}  $1${NC}"; echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"; }

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
   error "This script must be run as root (use sudo bash)"
fi

#===============================================================================
# SIS1: BASE SYSTEM SETUP
#===============================================================================
section "SIS1: BASE SYSTEM SETUP"

info "Updating system packages..."
apt-get update -y
apt-get upgrade -y

info "Installing base packages..."
apt-get install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    cron \
    logrotate \
    sudo \
    python3 \
    python3-pip \
    python3-venv

log "Base packages installed"

# Install PostgreSQL 14
section "SIS1: INSTALLING POSTGRESQL"

info "Adding PostgreSQL repository..."
sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
apt-get update

info "Installing PostgreSQL 14..."
apt-get install -y postgresql-14 postgresql-contrib-14

# Start PostgreSQL
systemctl enable postgresql
systemctl start postgresql

log "PostgreSQL installed"

#===============================================================================
# SIS2: GROUPS CREATION
#===============================================================================
section "SIS2: CREATING GROUPS"

# Create groups with specific GIDs
create_group() {
    local name=$1
    local gid=$2
    if ! getent group "$name" > /dev/null 2>&1; then
        groupadd -g "$gid" "$name"
        log "Created group: $name (GID: $gid)"
    else
        info "Group already exists: $name"
    fi
}

create_group "dapmeet" "2000"
create_group "devops" "2001"
create_group "automation" "2002"
create_group "monitoring" "2003"
create_group "auditor" "2004"
create_group "sysadmin" "2020"
create_group "dba" "2011"
create_group "backup" "2012"

# Ensure docker group exists (will be created by Docker install later)
if ! getent group docker > /dev/null 2>&1; then
    groupadd docker
    log "Created group: docker"
fi

# postgres group is created by PostgreSQL installation
info "postgres group exists (created by PostgreSQL)"

#===============================================================================
# SIS2: USERS CREATION
#===============================================================================
section "SIS2: CREATING USERS"

# postgres user is created by PostgreSQL installation
if id "postgres" > /dev/null 2>&1; then
    info "User already exists: postgres (created by PostgreSQL)"
fi

# dapmeet-backend user
if ! id "dapmeet-backend" > /dev/null 2>&1; then
    useradd -r -u 1002 -g dapmeet -s /bin/bash -d /opt/dapmeet/backend -c "FastAPI backend service" dapmeet-backend
    log "Created system user: dapmeet-backend"
else
    info "User already exists: dapmeet-backend"
fi

# dapmeet-worker user
if ! id "dapmeet-worker" > /dev/null 2>&1; then
    useradd -r -u 1003 -g dapmeet -s /bin/bash -d /opt/dapmeet/backend -c "Background worker for transcriptions" dapmeet-worker
    log "Created system user: dapmeet-worker"
else
    info "User already exists: dapmeet-worker"
fi

# backup user
if ! id "backup" > /dev/null 2>&1; then
    useradd -r -u 1004 -g backup -G postgres -s /bin/bash -d /var/backups -c "Backup automation" backup
    log "Created system user: backup"
else
    usermod -aG postgres backup 2>/dev/null || true
    info "User already exists: backup"
fi

# Sysadmin user
if ! id "sysadmin" > /dev/null 2>&1; then
    useradd -m -u 1020 -g sysadmin -G sudo -s /bin/bash -c "System administrator" sysadmin
    log "Created user: sysadmin"
else
    usermod -aG sudo sysadmin 2>/dev/null || true
    info "User already exists: sysadmin"
fi

# DevOps user
if ! id "devops_user" > /dev/null 2>&1; then
    useradd -m -u 1021 -g devops -G dapmeet -s /bin/bash -c "DevOps engineer" devops_user
    log "Created user: devops_user"
else
    usermod -aG dapmeet devops_user 2>/dev/null || true
    info "User already exists: devops_user"
fi

# DBA user
if ! id "dba_user" > /dev/null 2>&1; then
    useradd -m -u 1022 -g dba -G postgres -s /bin/bash -c "Database administrator" dba_user
    log "Created user: dba_user"
else
    usermod -aG postgres dba_user 2>/dev/null || true
    info "User already exists: dba_user"
fi

# Automation user
if ! id "automation" > /dev/null 2>&1; then
    useradd -m -u 1030 -g automation -G dapmeet -s /bin/bash -c "CI/CD automation bot" automation
    log "Created user: automation"
else
    usermod -aG dapmeet automation 2>/dev/null || true
    info "User already exists: automation"
fi

# Monitoring user
if ! id "monitoring" > /dev/null 2>&1; then
    useradd -m -u 1040 -g monitoring -s /bin/bash -c "System monitoring" monitoring
    log "Created user: monitoring"
else
    info "User already exists: monitoring"
fi

# Auditor user
if ! id "auditor" > /dev/null 2>&1; then
    useradd -m -u 1050 -g auditor -s /bin/bash -c "Security auditor" auditor
    log "Created user: auditor"
else
    info "User already exists: auditor"
fi

log "All users created"

#===============================================================================
# SIS2: DIRECTORY STRUCTURE & PERMISSIONS
#===============================================================================
section "SIS2: CREATING DIRECTORIES & SETTING PERMISSIONS"

# Create directory structure
mkdir -p /opt/dapmeet
mkdir -p /opt/dapmeet/backend
mkdir -p /opt/dapmeet/scripts
mkdir -p /var/dapmeet
mkdir -p /var/dapmeet/processing
mkdir -p /var/log/dapmeet
mkdir -p /var/backups/dapmeet
mkdir -p /var/backups/dapmeet/postgresql
mkdir -p /var/backups/dapmeet/configs
mkdir -p /etc/dapmeet
mkdir -p /etc/dapmeet/backend
mkdir -p /tmp/dapmeet-setup

log "Created all directories"

# Set ownership and permissions
chown dapmeet-backend:dapmeet /opt/dapmeet/backend
chmod 755 /opt/dapmeet/backend

chown root:dapmeet /opt/dapmeet/scripts
chmod 755 /opt/dapmeet/scripts

chown dapmeet-backend:dapmeet /var/dapmeet
chmod 755 /var/dapmeet

chown dapmeet-worker:dapmeet /var/dapmeet/processing
chmod 755 /var/dapmeet/processing

chown root:dapmeet /var/log/dapmeet
chmod 755 /var/log/dapmeet

chown backup:postgres /var/backups/dapmeet/postgresql
chmod 750 /var/backups/dapmeet/postgresql

chown root:dapmeet /var/backups/dapmeet/configs
chmod 750 /var/backups/dapmeet/configs

chown root:dapmeet /etc/dapmeet/backend
chmod 750 /etc/dapmeet/backend

chown root:dapmeet /tmp/dapmeet-setup
chmod 775 /tmp/dapmeet-setup

# Protect .env files if they exist
touch /opt/dapmeet/backend/.env
chown dapmeet-backend:dapmeet /opt/dapmeet/backend/.env
chmod 600 /opt/dapmeet/backend/.env

log "Directory permissions configured"

#===============================================================================
# SIS2: SUDOERS CONFIGURATION
#===============================================================================
section "SIS2: CONFIGURING SUDOERS"

# DevOps sudoers
cat > /etc/sudoers.d/devops << 'EOF'
# DevOps group permissions for Backend VM
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl status dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop dapmeet-*
%devops ALL=(ALL) NOPASSWD: /usr/bin/docker *
EOF
chmod 440 /etc/sudoers.d/devops
log "Created sudoers: devops"

# DBA sudoers
cat > /etc/sudoers.d/dba << 'EOF'
# DBA group permissions for Backend VM
%dba ALL=(postgres) NOPASSWD: /usr/bin/psql
%dba ALL=(postgres) NOPASSWD: /usr/bin/pg_dump
%dba ALL=(postgres) NOPASSWD: /usr/bin/pg_restore
%dba ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart postgresql
%dba ALL=(ALL) NOPASSWD: /usr/bin/systemctl status postgresql
EOF
chmod 440 /etc/sudoers.d/dba
log "Created sudoers: dba"

# Automation sudoers
cat > /etc/sudoers.d/automation << 'EOF'
# Automation permissions for Backend VM
automation ALL=(ALL) NOPASSWD: /opt/dapmeet/scripts/deploy.sh
automation ALL=(ALL) NOPASSWD: /opt/dapmeet/scripts/*
automation ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-*
automation ALL=(dapmeet-backend) NOPASSWD: ALL
automation ALL=(dapmeet-worker) NOPASSWD: ALL
automation ALL=(ALL) NOPASSWD: /usr/bin/docker *
EOF
chmod 440 /etc/sudoers.d/automation
log "Created sudoers: automation"

# Backup sudoers
cat > /etc/sudoers.d/backup << 'EOF'
# Backup user permissions for Backend VM
backup ALL=(postgres) NOPASSWD: /usr/bin/pg_dump
backup ALL=(postgres) NOPASSWD: /usr/bin/pg_dumpall
backup ALL=(ALL) NOPASSWD: /usr/bin/tar
backup ALL=(ALL) NOPASSWD: /usr/bin/rsync
EOF
chmod 440 /etc/sudoers.d/backup
log "Created sudoers: backup"

# Monitoring sudoers
cat > /etc/sudoers.d/monitoring << 'EOF'
# Monitoring permissions for Backend VM
monitoring ALL=(ALL) NOPASSWD: /usr/bin/systemctl status *
monitoring ALL=(ALL) NOPASSWD: /usr/bin/journalctl *
monitoring ALL=(postgres) NOPASSWD: /usr/bin/psql -c "SELECT *"
EOF
chmod 440 /etc/sudoers.d/monitoring
log "Created sudoers: monitoring"

# Validate sudoers
visudo -cf /etc/sudoers.d/devops && log "Validated: devops sudoers"
visudo -cf /etc/sudoers.d/dba && log "Validated: dba sudoers"
visudo -cf /etc/sudoers.d/automation && log "Validated: automation sudoers"
visudo -cf /etc/sudoers.d/backup && log "Validated: backup sudoers"
visudo -cf /etc/sudoers.d/monitoring && log "Validated: monitoring sudoers"

#===============================================================================
# SIS2: SSH CONFIGURATION
#===============================================================================
section "SIS2: CONFIGURING SSH"

# Backup original sshd_config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Configure SSH
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#\?MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config
sed -i 's/^#\?ClientAliveInterval.*/ClientAliveInterval 300/' /etc/ssh/sshd_config

log "SSH configuration updated"

# Create .ssh directories for users with SSH access
for user in sysadmin devops_user dba_user automation auditor; do
    if id "$user" > /dev/null 2>&1; then
        home_dir=$(getent passwd "$user" | cut -d: -f6)
        if [ -n "$home_dir" ]; then
            mkdir -p "$home_dir/.ssh"
            chmod 700 "$home_dir/.ssh"
            touch "$home_dir/.ssh/authorized_keys"
            chmod 600 "$home_dir/.ssh/authorized_keys"
            chown -R "$user":"$(id -gn "$user")" "$home_dir/.ssh"
            log "Created SSH directory for: $user"
        fi
    fi
done

# Restart SSH
systemctl restart sshd
log "SSH service restarted"

#===============================================================================
# SIS3: FIREWALL CONFIGURATION
#===============================================================================
section "SIS3: CONFIGURING FIREWALL (UFW)"

# Reset UFW
ufw --force reset

# Set default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH
ufw allow 22/tcp comment 'SSH'

# Allow Backend API
ufw allow 8000/tcp comment 'Backend API'

# Allow PostgreSQL (from internal network only)
ufw allow from 10.0.0.0/8 to any port 5432 proto tcp comment 'PostgreSQL internal'
ufw allow from 192.168.0.0/16 to any port 5432 proto tcp comment 'PostgreSQL private'

# Allow from internal network
ufw allow from 10.0.0.0/8 comment 'Internal network'
ufw allow from 192.168.0.0/16 comment 'Private network'

# Enable UFW
ufw --force enable

# Enable logging
ufw logging on

log "Firewall configured and enabled"
ufw status verbose

#===============================================================================
# SIS4: DOCKER INSTALLATION
#===============================================================================
section "SIS4: INSTALLING DOCKER"

# Detect OS (Ubuntu or Debian)
. /etc/os-release
if [ "$ID" = "debian" ]; then
    DOCKER_OS="debian"
    DOCKER_CODENAME="$VERSION_CODENAME"
elif [ "$ID" = "ubuntu" ]; then
    DOCKER_OS="ubuntu"
    DOCKER_CODENAME="${UBUNTU_CODENAME:-$VERSION_CODENAME}"
else
    DOCKER_OS="debian"
    DOCKER_CODENAME="bookworm"
fi

info "Detected OS: $DOCKER_OS ($DOCKER_CODENAME)"

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL "https://download.docker.com/linux/$DOCKER_OS/gpg" -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$DOCKER_OS $DOCKER_CODENAME stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker
systemctl enable docker
systemctl start docker

# Add users to docker group
usermod -aG docker devops_user 2>/dev/null || true
usermod -aG docker automation 2>/dev/null || true
usermod -aG docker dapmeet-backend 2>/dev/null || true

log "Docker installed: $(docker --version)"

# Configure Docker daemon
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

systemctl restart docker
log "Docker daemon configured"

#===============================================================================
# SIS4: PULL DOCKER IMAGE & CREATE CONTAINER
#===============================================================================
section "SIS4: PULLING BACKEND DOCKER IMAGE"

# Pull the backend image
docker pull abdusss111/dapmeet-service:latest || warn "Could not pull image - will try later"

log "Docker image pulled (or will be pulled on service start)"

#===============================================================================
# SIS4: SYSTEMD SERVICE
#===============================================================================
section "SIS4: CREATING SYSTEMD SERVICE"

cat > /etc/systemd/system/dapmeet-backend.service << 'EOF'
[Unit]
Description=Dapmeet Backend Docker Container
Requires=docker.service
After=docker.service network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=10
ExecStartPre=-/usr/bin/docker stop dapmeet-backend
ExecStartPre=-/usr/bin/docker rm dapmeet-backend
ExecStartPre=/usr/bin/docker pull abdusss111/dapmeet-service:latest
ExecStart=/usr/bin/docker run --rm --name dapmeet-backend \
    -p 8000:8000 \
    -e PYTHONUNBUFFERED=1 \
    -e ENV=production \
    -v /opt/dapmeet/backend/.env:/app/.env:ro \
    -v /var/dapmeet:/app/data \
    -v /var/log/dapmeet:/app/logs \
    abdusss111/dapmeet-service:latest
ExecStop=/usr/bin/docker stop dapmeet-backend

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable dapmeet-backend
log "Systemd service created: dapmeet-backend"

# Try to start the service
systemctl start dapmeet-backend || warn "Service start failed - image may need to be available first"

#===============================================================================
# SIS4: CRON JOBS & MAINTENANCE SCRIPTS
#===============================================================================
section "SIS4: CREATING MAINTENANCE SCRIPTS"

# PostgreSQL backup script
cat > /opt/dapmeet/scripts/backup_postgres.sh << 'EOF'
#!/bin/bash
# PostgreSQL daily backup script
# Runs daily at 3:00 AM

set -e

BACKUP_DIR="/var/backups/dapmeet/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/dapmeet_$DATE.sql.gz"

mkdir -p "$BACKUP_DIR"

# Create backup using pg_dump
sudo -u postgres pg_dump dapmeet 2>/dev/null | gzip > "$BACKUP_FILE" || {
    # If dapmeet db doesn't exist, backup all databases
    sudo -u postgres pg_dumpall | gzip > "$BACKUP_DIR/all_databases_$DATE.sql.gz"
}

# Set proper permissions
chown backup:postgres "$BACKUP_FILE" 2>/dev/null || true
chmod 640 "$BACKUP_FILE" 2>/dev/null || true

# Remove backups older than 7 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete

echo "[$(date)] PostgreSQL backup completed"
EOF
chmod 755 /opt/dapmeet/scripts/backup_postgres.sh
log "Created script: backup_postgres.sh"

# Cleanup processing files script
cat > /opt/dapmeet/scripts/cleanup_processing.sh << 'EOF'
#!/bin/bash
# Clean old processing files script
# Runs daily at 4:30 AM

set -e

PROCESSING_DIR="/var/dapmeet/processing"
DAYS_OLD=3

# Remove processing files older than specified days
find "$PROCESSING_DIR" -type f -mtime +$DAYS_OLD -delete 2>/dev/null || true

# Remove empty directories
find "$PROCESSING_DIR" -type d -empty -delete 2>/dev/null || true

echo "[$(date)] Processing cleanup completed: removed files older than $DAYS_OLD days"
EOF
chmod 755 /opt/dapmeet/scripts/cleanup_processing.sh
log "Created script: cleanup_processing.sh"

# Backend logs rotation script
cat > /opt/dapmeet/scripts/rotate_backend_logs.sh << 'EOF'
#!/bin/bash
# Backend logs rotation script
# Runs weekly on Sundays at 5:00 AM

set -e

LOG_DIR="/var/log/dapmeet"
MAX_SIZE="100M"
ROTATE_COUNT=5

# Rotate logs using logrotate
cat > /tmp/dapmeet-logrotate.conf << CONF
$LOG_DIR/*.log {
    size $MAX_SIZE
    rotate $ROTATE_COUNT
    compress
    delaycompress
    missingok
    notifempty
    create 640 root dapmeet
}
CONF

/usr/sbin/logrotate -f /tmp/dapmeet-logrotate.conf

rm -f /tmp/dapmeet-logrotate.conf

echo "[$(date)] Backend logs rotation completed"
EOF
chmod 755 /opt/dapmeet/scripts/rotate_backend_logs.sh
log "Created script: rotate_backend_logs.sh"

# Docker cleanup script
cat > /opt/dapmeet/scripts/docker_cleanup.sh << 'EOF'
#!/bin/bash
# Docker cleanup script
# Removes unused images and containers

set -e

echo "[$(date)] Starting Docker cleanup..."

# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -af

# Remove unused volumes
docker volume prune -f

echo "[$(date)] Docker cleanup completed"
EOF
chmod 755 /opt/dapmeet/scripts/docker_cleanup.sh
log "Created script: docker_cleanup.sh"

# Deploy script
cat > /opt/dapmeet/scripts/deploy.sh << 'EOF'
#!/bin/bash
# Deployment script for dapmeet-backend

set -e

echo "[$(date)] Starting deployment..."

# Pull latest image
docker pull abdusss111/dapmeet-service:latest

# Restart the service
systemctl restart dapmeet-backend

# Wait for service to be healthy
sleep 10

# Check status
systemctl status dapmeet-backend --no-pager

echo "[$(date)] Deployment completed"
EOF
chmod 755 /opt/dapmeet/scripts/deploy.sh
log "Created script: deploy.sh"

#===============================================================================
# SIS4: CONFIGURE CRON JOBS
#===============================================================================
section "SIS4: CONFIGURING CRON JOBS"

# Create cron jobs for root
(crontab -l 2>/dev/null | grep -v "dapmeet" || true; echo "# Dapmeet Backend Maintenance Jobs") | crontab -
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/dapmeet/scripts/backup_postgres.sh >> /var/log/dapmeet/pg_backup.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "30 4 * * * /opt/dapmeet/scripts/cleanup_processing.sh >> /var/log/dapmeet/cleanup.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "0 5 * * 0 /opt/dapmeet/scripts/rotate_backend_logs.sh >> /var/log/dapmeet/logrotate.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "0 4 * * 0 /opt/dapmeet/scripts/docker_cleanup.sh >> /var/log/dapmeet/docker_cleanup.log 2>&1") | crontab -

log "Cron jobs configured"

echo ""
echo "=== Cron Jobs (root) ==="
crontab -l

#===============================================================================
# POSTGRESQL DATABASE SETUP
#===============================================================================
section "CONFIGURING POSTGRESQL"

# Create dapmeet database and user
sudo -u postgres psql << 'EOF'
-- Create dapmeet database if not exists
SELECT 'CREATE DATABASE dapmeet' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dapmeet')\gexec

-- Create dapmeet user if not exists
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'dapmeet_app') THEN
      CREATE USER dapmeet_app WITH PASSWORD 'dapmeet_secure_password';
   END IF;
END
$do$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE dapmeet TO dapmeet_app;
EOF

log "PostgreSQL database and user created"

# Configure PostgreSQL to allow connections
PG_HBA="/etc/postgresql/14/main/pg_hba.conf"
if ! grep -q "dapmeet_app" "$PG_HBA"; then
    echo "# Dapmeet application" >> "$PG_HBA"
    echo "host    dapmeet         dapmeet_app     127.0.0.1/32            md5" >> "$PG_HBA"
    echo "host    dapmeet         dapmeet_app     10.0.0.0/8              md5" >> "$PG_HBA"
    echo "host    dapmeet         dapmeet_app     192.168.0.0/16          md5" >> "$PG_HBA"
    systemctl reload postgresql
    log "PostgreSQL pg_hba.conf updated"
fi

# Update postgresql.conf to listen on all interfaces (for internal access)
PG_CONF="/etc/postgresql/14/main/postgresql.conf"
sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
systemctl reload postgresql
log "PostgreSQL configured to listen on all interfaces"

#===============================================================================
# FINAL VERIFICATION
#===============================================================================
section "VERIFICATION"

echo ""
echo "=== System Information ==="
echo "Hostname: $(hostname)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2)"
echo "Kernel: $(uname -r)"
echo ""

echo "=== Groups Created ==="
for group in dapmeet devops automation monitoring auditor sysadmin dba backup docker postgres; do
    getent group "$group" 2>/dev/null | cut -d: -f1,3 || echo "$group: not found"
done
echo ""

echo "=== Users Created ==="
for user in postgres dapmeet-backend dapmeet-worker backup sysadmin devops_user dba_user automation monitoring auditor; do
    id "$user" 2>/dev/null | head -1 || echo "$user: not found"
done
echo ""

echo "=== PostgreSQL Status ==="
systemctl status postgresql --no-pager | head -5
sudo -u postgres psql -c "\l" 2>/dev/null | head -10 || true
echo ""

echo "=== Docker Status ==="
docker --version
docker ps -a
echo ""

echo "=== Systemd Services ==="
systemctl status dapmeet-backend --no-pager || true
echo ""

echo "=== Firewall Status ==="
ufw status
echo ""

echo "=== Cron Jobs ==="
crontab -l
echo ""

echo "=== Directory Structure ==="
ls -la /opt/dapmeet/
ls -la /var/dapmeet/
ls -la /var/log/dapmeet/
echo ""

echo "=== Scripts Created ==="
ls -la /opt/dapmeet/scripts/
echo ""

section "SETUP COMPLETE!"
log "Backend VM setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Add SSH public keys to users' ~/.ssh/authorized_keys"
echo "2. Update /opt/dapmeet/backend/.env with your configuration"
echo "3. Change PostgreSQL password: ALTER USER dapmeet_app WITH PASSWORD 'new_password';"
echo "4. Ensure Docker image is available and service is running"
echo ""
echo "Commands to check status:"
echo "  systemctl status dapmeet-backend"
echo "  systemctl status postgresql"
echo "  docker ps"
echo "  ufw status"
echo "  sudo -u postgres psql -c '\\l'"
