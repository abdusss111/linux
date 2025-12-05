#!/bin/bash
#==============================================================================
# Common Library Functions for Dapmeet Setup Scripts
# Source this file in other scripts: source "$(dirname "$0")/../common/lib.sh"
#==============================================================================

# Colors for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export MAGENTA='\033[0;35m'
export NC='\033[0m' # No Color

# Logging functions
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "${CYAN}[STEP]${NC} $1"; }
log_skip()    { echo -e "${MAGENTA}[SKIP]${NC} $1"; }

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root. Use: sudo $0"
        exit 1
    fi
}

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check if a service exists
service_exists() {
    systemctl list-unit-files "$1.service" &> /dev/null
}

# Check if a service is running
service_is_running() {
    systemctl is-active --quiet "$1" 2>/dev/null
}

# Check if a service is enabled
service_is_enabled() {
    systemctl is-enabled --quiet "$1" 2>/dev/null
}

# Enable and start a service (idempotent)
ensure_service_running() {
    local service=$1
    
    if ! service_exists "$service"; then
        log_warning "Service $service does not exist"
        return 1
    fi
    
    if ! service_is_enabled "$service"; then
        systemctl enable "$service"
        log_info "Enabled service: $service"
    fi
    
    if ! service_is_running "$service"; then
        systemctl start "$service"
        log_info "Started service: $service"
    else
        log_skip "Service $service is already running"
    fi
}

# Check if a group exists
group_exists() {
    getent group "$1" &> /dev/null
}

# Check if a user exists
user_exists() {
    id "$1" &> /dev/null
}

# Create group if not exists (idempotent)
ensure_group() {
    local group=$1
    if group_exists "$group"; then
        log_skip "Group '$group' already exists"
    else
        groupadd -f "$group"
        log_success "Created group: $group"
    fi
}

# Create user if not exists (idempotent)
ensure_user() {
    local user=$1
    local group=$2
    local home=$3
    local shell=${4:-/bin/bash}
    local system_user=${5:-false}
    
    if user_exists "$user"; then
        log_skip "User '$user' already exists"
        return 0
    fi
    
    local cmd="useradd"
    
    if [ "$system_user" = "true" ]; then
        cmd="$cmd -r"
    else
        cmd="$cmd -m"
    fi
    
    if [ -n "$home" ]; then
        cmd="$cmd -d $home"
    fi
    
    cmd="$cmd -s $shell -g $group $user"
    
    eval $cmd 2>/dev/null && log_success "Created user: $user" || log_warning "User $user might already exist"
}

# Add user to group (idempotent)
ensure_user_in_group() {
    local user=$1
    local group=$2
    
    if ! user_exists "$user"; then
        log_warning "User $user does not exist"
        return 1
    fi
    
    if id -nG "$user" | grep -qw "$group"; then
        log_skip "User '$user' is already in group '$group'"
    else
        usermod -aG "$group" "$user"
        log_success "Added user $user to group: $group"
    fi
}

# Create directory with permissions (idempotent)
ensure_directory() {
    local dir=$1
    local owner=${2:-root:root}
    local mode=${3:-755}
    
    if [ -d "$dir" ]; then
        log_skip "Directory '$dir' already exists"
    else
        mkdir -p "$dir"
        log_success "Created directory: $dir"
    fi
    
    chown "$owner" "$dir"
    chmod "$mode" "$dir"
}

# Install package if not installed (idempotent)
ensure_package() {
    local package=$1
    
    if dpkg -l "$package" 2>/dev/null | grep -q "^ii"; then
        log_skip "Package '$package' is already installed"
        return 0
    fi
    
    log_info "Installing package: $package"
    apt-get install -y "$package" > /dev/null 2>&1
    log_success "Installed package: $package"
}

# Update apt cache if older than specified hours
ensure_apt_updated() {
    local max_age_hours=${1:-24}
    local apt_last_update="/var/lib/apt/periodic/update-success-stamp"
    
    if [ -f "$apt_last_update" ]; then
        local last_update=$(stat -c %Y "$apt_last_update" 2>/dev/null || echo 0)
        local now=$(date +%s)
        local age_hours=$(( (now - last_update) / 3600 ))
        
        if [ $age_hours -lt $max_age_hours ]; then
            log_skip "Apt cache is recent (${age_hours}h old, max ${max_age_hours}h)"
            return 0
        fi
    fi
    
    log_info "Updating apt cache..."
    apt-get update > /dev/null 2>&1
    log_success "Apt cache updated"
}

# Create sudoers file (idempotent)
ensure_sudoers() {
    local filename=$1
    local content=$2
    local filepath="/etc/sudoers.d/$filename"
    
    echo "$content" > "$filepath"
    chmod 440 "$filepath"
    
    # Validate sudoers file
    if visudo -c -f "$filepath" > /dev/null 2>&1; then
        log_success "Created/updated sudoers file: $filename"
    else
        rm -f "$filepath"
        log_error "Invalid sudoers file: $filename - removed"
        return 1
    fi
}

# Check if firewall rule exists
ufw_rule_exists() {
    local rule=$1
    ufw status | grep -q "$rule"
}

# Add UFW rule (idempotent)
ensure_ufw_rule() {
    local rule=$1
    
    if ufw_rule_exists "$rule"; then
        log_skip "UFW rule '$rule' already exists"
    else
        ufw allow $rule > /dev/null 2>&1
        log_success "Added UFW rule: $rule"
    fi
}

# Install Docker (idempotent)
ensure_docker() {
    if command_exists docker; then
        log_skip "Docker is already installed: $(docker --version | head -1)"
        ensure_service_running docker
        return 0
    fi
    
    log_info "Installing Docker..."
    
    # Install prerequisites
    ensure_package ca-certificates
    ensure_package curl
    ensure_package gnupg
    ensure_package lsb-release
    
    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
        curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
    fi
    
    # Set up Docker repository
    local os_id=$(. /etc/os-release && echo "$ID")
    local version_codename=$(. /etc/os-release && echo "$VERSION_CODENAME")
    
    if [ ! -f /etc/apt/sources.list.d/docker.list ]; then
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${os_id} ${version_codename} stable" | \
            tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update > /dev/null 2>&1
    fi
    
    # Install Docker
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin > /dev/null 2>&1
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    log_success "Docker installed successfully"
}

# Install Node.js (idempotent)
ensure_nodejs() {
    local version=${1:-20}
    
    if command_exists node; then
        local installed_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$installed_version" -ge "$version" ]; then
            log_skip "Node.js is already installed: $(node --version)"
            return 0
        fi
    fi
    
    log_info "Installing Node.js $version..."
    
    if [ ! -f /etc/apt/sources.list.d/nodesource.list ]; then
        curl -fsSL https://deb.nodesource.com/setup_${version}.x | bash - > /dev/null 2>&1
    fi
    
    apt-get install -y nodejs > /dev/null 2>&1
    log_success "Node.js installed: $(node --version)"
}

# Install PostgreSQL (idempotent)
ensure_postgresql() {
    if command_exists psql && service_exists postgresql; then
        log_skip "PostgreSQL is already installed"
        ensure_service_running postgresql
        return 0
    fi
    
    log_info "Installing PostgreSQL..."
    apt-get install -y postgresql postgresql-contrib > /dev/null 2>&1
    
    systemctl start postgresql
    systemctl enable postgresql
    
    log_success "PostgreSQL installed"
}

# Create PostgreSQL database (idempotent)
ensure_pg_database() {
    local db_name=$1
    local db_user=$2
    local db_pass=$3
    
    # Check if database exists
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$db_name"; then
        log_skip "Database '$db_name' already exists"
    else
        sudo -u postgres psql -c "CREATE DATABASE $db_name;" 2>/dev/null
        log_success "Created database: $db_name"
    fi
    
    # Check if user exists
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$db_user'" | grep -q 1; then
        log_skip "PostgreSQL user '$db_user' already exists"
    else
        sudo -u postgres psql -c "CREATE USER $db_user WITH PASSWORD '$db_pass';" 2>/dev/null
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;" 2>/dev/null
        log_success "Created PostgreSQL user: $db_user"
    fi
}

# Copy file if source is newer or target doesn't exist
ensure_file_copied() {
    local src=$1
    local dst=$2
    local mode=${3:-644}
    
    if [ ! -f "$src" ]; then
        log_error "Source file not found: $src"
        return 1
    fi
    
    if [ -f "$dst" ]; then
        if [ "$src" -nt "$dst" ]; then
            cp "$src" "$dst"
            chmod "$mode" "$dst"
            log_success "Updated file: $dst"
        else
            log_skip "File '$dst' is up to date"
        fi
    else
        cp "$src" "$dst"
        chmod "$mode" "$dst"
        log_success "Copied file: $dst"
    fi
}

# Print section header
print_section() {
    echo ""
    echo "=============================================="
    echo -e "${CYAN}  $1${NC}"
    echo "=============================================="
    echo ""
}

# Print summary
print_summary() {
    local title=$1
    echo ""
    echo "=============================================="
    echo -e "${GREEN}  $title${NC}"
    echo "=============================================="
}

