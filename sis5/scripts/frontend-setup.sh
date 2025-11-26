#!/bin/bash
#===============================================================================
# Dapmeet Frontend VM Setup Script
# SIS1 → SIS5 Complete Implementation
# 
# Student: Abdurakhimov Abdussalam
# VM: Frontend (VM1)
# Run as: sudo bash ./frontend-setup.sh
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
    sudo

log "Base packages installed"

# Install Node.js 20 LTS
info "Installing Node.js 20 LTS..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
log "Node.js $(node --version) installed"

# Install Nginx
info "Installing Nginx..."
apt-get install -y nginx
systemctl enable nginx
log "Nginx installed"

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
create_group "deployer" "2010"

# Ensure docker group exists (will be created by Docker install later)
if ! getent group docker > /dev/null 2>&1; then
    groupadd docker
    log "Created group: docker"
fi

#===============================================================================
# SIS2: USERS CREATION
#===============================================================================
section "SIS2: CREATING USERS"

# System user: nginx (usually created by nginx package)
if ! id "nginx" > /dev/null 2>&1; then
    useradd -r -u 1001 -g www-data -s /usr/sbin/nologin -d /var/cache/nginx -c "Nginx web server" nginx 2>/dev/null || true
    log "Created system user: nginx"
fi

# Deployer user
if ! id "deployer" > /dev/null 2>&1; then
    useradd -m -u 1010 -g deployer -G dapmeet -s /bin/bash -c "Deployment specialist" deployer
    log "Created user: deployer"
else
    usermod -aG dapmeet deployer 2>/dev/null || true
    info "User already exists: deployer"
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
mkdir -p /opt/dapmeet/frontend
mkdir -p /opt/dapmeet/scripts
mkdir -p /var/log/dapmeet
mkdir -p /var/www/dapmeet
mkdir -p /var/www/dapmeet/static
mkdir -p /var/backups/dapmeet
mkdir -p /var/backups/dapmeet/logs
mkdir -p /etc/dapmeet
mkdir -p /etc/dapmeet/nginx
mkdir -p /etc/dapmeet/ssl
mkdir -p /tmp/dapmeet-setup

log "Created all directories"

# Set ownership and permissions
chown deployer:dapmeet /opt/dapmeet/frontend
chmod 755 /opt/dapmeet/frontend

chown root:dapmeet /opt/dapmeet/scripts
chmod 755 /opt/dapmeet/scripts

chown root:dapmeet /var/log/dapmeet
chmod 755 /var/log/dapmeet

chown www-data:www-data /var/www/dapmeet/static
chmod 755 /var/www/dapmeet/static

chown root:www-data /etc/dapmeet/nginx
chmod 750 /etc/dapmeet/nginx

chown root:www-data /etc/dapmeet/ssl
chmod 750 /etc/dapmeet/ssl

chown root:dapmeet /var/backups/dapmeet
chmod 755 /var/backups/dapmeet

chown root:dapmeet /tmp/dapmeet-setup
chmod 775 /tmp/dapmeet-setup

log "Directory permissions configured"

#===============================================================================
# SIS2: SUDOERS CONFIGURATION
#===============================================================================
section "SIS2: CONFIGURING SUDOERS"

# DevOps sudoers
cat > /etc/sudoers.d/devops << 'EOF'
# DevOps group permissions for Frontend VM
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl status nginx
%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
%devops ALL=(ALL) NOPASSWD: /usr/sbin/nginx -t
%devops ALL=(ALL) NOPASSWD: /usr/bin/docker *
EOF
chmod 440 /etc/sudoers.d/devops
log "Created sudoers: devops"

# Deployer sudoers
cat > /etc/sudoers.d/deployer << 'EOF'
# Deployer permissions for Frontend VM
deployer ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
deployer ALL=(ALL) NOPASSWD: /usr/bin/npm *
deployer ALL=(ALL) NOPASSWD: /usr/bin/docker *
EOF
chmod 440 /etc/sudoers.d/deployer
log "Created sudoers: deployer"

# Monitoring sudoers
cat > /etc/sudoers.d/monitoring << 'EOF'
# Monitoring permissions for Frontend VM
monitoring ALL=(ALL) NOPASSWD: /usr/bin/systemctl status *
monitoring ALL=(ALL) NOPASSWD: /usr/bin/journalctl *
EOF
chmod 440 /etc/sudoers.d/monitoring
log "Created sudoers: monitoring"

# Automation sudoers
cat > /etc/sudoers.d/automation << 'EOF'
# Automation permissions for Frontend VM
automation ALL=(ALL) NOPASSWD: /opt/dapmeet/scripts/*
automation ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-*
automation ALL=(ALL) NOPASSWD: /usr/bin/docker *
EOF
chmod 440 /etc/sudoers.d/automation
log "Created sudoers: automation"

# Validate sudoers
visudo -cf /etc/sudoers.d/devops && log "Validated: devops sudoers"
visudo -cf /etc/sudoers.d/deployer && log "Validated: deployer sudoers"
visudo -cf /etc/sudoers.d/monitoring && log "Validated: monitoring sudoers"
visudo -cf /etc/sudoers.d/automation && log "Validated: automation sudoers"

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
for user in deployer sysadmin devops_user automation auditor; do
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

# Allow HTTP
ufw allow 80/tcp comment 'HTTP'

# Allow HTTPS
ufw allow 443/tcp comment 'HTTPS'

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
usermod -aG docker deployer 2>/dev/null || true

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
section "SIS4: PULLING FRONTEND DOCKER IMAGE"

# Pull the frontend image
docker pull abdusss111/dapmeet-client:latest || warn "Could not pull image - will try later"

log "Docker image pulled (or will be pulled on service start)"

#===============================================================================
# SIS4: SYSTEMD SERVICE
#===============================================================================
section "SIS4: CREATING SYSTEMD SERVICE"

cat > /etc/systemd/system/dapmeet-frontend.service << 'EOF'
[Unit]
Description=Dapmeet Frontend Docker Container
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=10
ExecStartPre=-/usr/bin/docker stop dapmeet-frontend
ExecStartPre=-/usr/bin/docker rm dapmeet-frontend
ExecStartPre=/usr/bin/docker pull abdusss111/dapmeet-client:latest
ExecStart=/usr/bin/docker run --rm --name dapmeet-frontend \
    -p 3000:3000 \
    -e NODE_ENV=production \
    abdusss111/dapmeet-client:latest
ExecStop=/usr/bin/docker stop dapmeet-frontend

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable dapmeet-frontend
log "Systemd service created: dapmeet-frontend"

# Try to start the service
systemctl start dapmeet-frontend || warn "Service start failed - image may need to be available first"

#===============================================================================
# SIS4: CRON JOBS & MAINTENANCE SCRIPTS
#===============================================================================
section "SIS4: CREATING MAINTENANCE SCRIPTS"

# Backup frontend logs script
cat > /opt/dapmeet/scripts/backup_frontend_logs.sh << 'EOF'
#!/bin/bash
# Frontend logs backup script
# Runs daily at 2:00 AM

set -e

BACKUP_DIR="/var/backups/dapmeet/logs"
LOG_DIR="/var/log/dapmeet"
DATE=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR"

# Compress and backup logs
tar -czf "$BACKUP_DIR/frontend_logs_$DATE.tar.gz" -C "$LOG_DIR" . 2>/dev/null || true

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "frontend_logs_*.tar.gz" -mtime +30 -delete

echo "[$(date)] Frontend logs backup completed"
EOF
chmod 755 /opt/dapmeet/scripts/backup_frontend_logs.sh
log "Created script: backup_frontend_logs.sh"

# SSL certificate check script
cat > /opt/dapmeet/scripts/check_ssl_renewal.sh << 'EOF'
#!/bin/bash
# SSL certificate renewal check script
# Runs weekly on Mondays at 6:00 AM

set -e

SSL_DIR="/etc/dapmeet/ssl"
DAYS_WARNING=30

if [ -f "$SSL_DIR/fullchain.pem" ]; then
    EXPIRY=$(openssl x509 -enddate -noout -in "$SSL_DIR/fullchain.pem" | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
    
    if [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
        echo "[$(date)] WARNING: SSL certificate expires in $DAYS_LEFT days!"
    else
        echo "[$(date)] SSL certificate OK: $DAYS_LEFT days remaining"
    fi
else
    echo "[$(date)] No SSL certificate found at $SSL_DIR/fullchain.pem"
fi
EOF
chmod 755 /opt/dapmeet/scripts/check_ssl_renewal.sh
log "Created script: check_ssl_renewal.sh"

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

#===============================================================================
# SIS4: CONFIGURE CRON JOBS
#===============================================================================
section "SIS4: CONFIGURING CRON JOBS"

# Create cron jobs
(crontab -l 2>/dev/null | grep -v "dapmeet" || true; echo "# Dapmeet Frontend Maintenance Jobs") | crontab -
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/dapmeet/scripts/backup_frontend_logs.sh >> /var/log/dapmeet/backup.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "0 6 * * 1 /opt/dapmeet/scripts/check_ssl_renewal.sh >> /var/log/dapmeet/ssl_check.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "0 4 * * 0 /opt/dapmeet/scripts/docker_cleanup.sh >> /var/log/dapmeet/docker_cleanup.log 2>&1") | crontab -

log "Cron jobs configured"
crontab -l

#===============================================================================
# NGINX CONFIGURATION (Reverse Proxy for Frontend)
#===============================================================================
section "CONFIGURING NGINX REVERSE PROXY"

cat > /etc/nginx/sites-available/dapmeet << 'EOF'
# Dapmeet Frontend Nginx Configuration

upstream dapmeet_frontend {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name _;

    # Logging
    access_log /var/log/dapmeet/nginx_access.log;
    error_log /var/log/dapmeet/nginx_error.log;

    # Proxy to Next.js frontend
    location / {
        proxy_pass http://dapmeet_frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Static files
    location /static/ {
        alias /var/www/dapmeet/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/dapmeet /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
nginx -t && systemctl reload nginx
log "Nginx configured as reverse proxy"

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
for group in dapmeet devops automation monitoring auditor sysadmin deployer docker; do
    getent group "$group" 2>/dev/null | cut -d: -f1,3 || echo "$group: not found"
done
echo ""

echo "=== Users Created ==="
for user in deployer sysadmin devops_user automation monitoring auditor; do
    id "$user" 2>/dev/null | head -1 || echo "$user: not found"
done
echo ""

echo "=== Docker Status ==="
docker --version
docker ps -a
echo ""

echo "=== Systemd Services ==="
systemctl status dapmeet-frontend --no-pager || true
echo ""

echo "=== Firewall Status ==="
ufw status
echo ""

echo "=== Cron Jobs ==="
crontab -l
echo ""

echo "=== Directory Structure ==="
ls -la /opt/dapmeet/
ls -la /var/log/dapmeet/
echo ""

section "SETUP COMPLETE!"
log "Frontend VM setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Add SSH public keys to users' ~/.ssh/authorized_keys"
echo "2. Configure SSL certificates in /etc/dapmeet/ssl/"
echo "3. Update Nginx config for your domain"
echo "4. Ensure Docker image is available and service is running"
echo ""
echo "Commands to check status:"
echo "  systemctl status dapmeet-frontend"
echo "  docker ps"
echo "  ufw status"
echo "  nginx -t && systemctl status nginx"
