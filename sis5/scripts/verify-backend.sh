#!/bin/bash
#===============================================================================
# Dapmeet Backend VM Verification Script
# Run this after setup to verify all components
#===============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

echo "============================================="
echo "  Dapmeet Backend VM Verification"
echo "============================================="
echo ""

# Check groups
echo "=== Checking Groups ==="
groups=("dapmeet" "devops" "automation" "monitoring" "auditor" "sysadmin" "dba" "backup" "docker" "postgres")
for g in "${groups[@]}"; do
    if getent group "$g" > /dev/null 2>&1; then
        pass "Group exists: $g"
    else
        fail "Group missing: $g"
    fi
done

echo ""
echo "=== Checking Users ==="
users=("postgres" "dapmeet-backend" "dapmeet-worker" "backup" "sysadmin" "devops_user" "dba_user" "automation" "monitoring" "auditor")
for u in "${users[@]}"; do
    if id "$u" > /dev/null 2>&1; then
        pass "User exists: $u"
    else
        fail "User missing: $u"
    fi
done

echo ""
echo "=== Checking Directories ==="
dirs=(
    "/opt/dapmeet/backend"
    "/opt/dapmeet/scripts"
    "/var/dapmeet"
    "/var/dapmeet/processing"
    "/var/log/dapmeet"
    "/var/backups/dapmeet/postgresql"
    "/etc/dapmeet/backend"
)
for d in "${dirs[@]}"; do
    if [ -d "$d" ]; then
        pass "Directory exists: $d"
    else
        fail "Directory missing: $d"
    fi
done

echo ""
echo "=== Checking Sudoers ==="
sudoers=("devops" "dba" "automation" "backup" "monitoring")
for s in "${sudoers[@]}"; do
    if [ -f "/etc/sudoers.d/$s" ]; then
        if visudo -cf "/etc/sudoers.d/$s" > /dev/null 2>&1; then
            pass "Sudoers valid: $s"
        else
            fail "Sudoers invalid: $s"
        fi
    else
        fail "Sudoers missing: $s"
    fi
done

echo ""
echo "=== Checking Services ==="

# PostgreSQL
if systemctl is-active --quiet postgresql; then
    pass "PostgreSQL is running"
else
    fail "PostgreSQL is not running"
fi

# Docker
if systemctl is-active --quiet docker; then
    pass "Docker is running"
else
    fail "Docker is not running"
fi

# Dapmeet Backend
if systemctl is-enabled --quiet dapmeet-backend 2>/dev/null; then
    pass "dapmeet-backend service is enabled"
    if systemctl is-active --quiet dapmeet-backend; then
        pass "dapmeet-backend service is running"
    else
        warn "dapmeet-backend service is not running (may need image)"
    fi
else
    fail "dapmeet-backend service not found"
fi

echo ""
echo "=== Checking Firewall ==="
if ufw status | grep -q "Status: active"; then
    pass "UFW is active"
    ufw status | grep -E "22|8000|5432" | while read line; do
        echo "     $line"
    done
else
    fail "UFW is not active"
fi

echo ""
echo "=== Checking PostgreSQL Database ==="
if sudo -u postgres psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw dapmeet; then
    pass "Database 'dapmeet' exists"
else
    warn "Database 'dapmeet' not found"
fi

if sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='dapmeet_app'" 2>/dev/null | grep -q 1; then
    pass "User 'dapmeet_app' exists"
else
    warn "User 'dapmeet_app' not found"
fi

echo ""
echo "=== Checking Cron Jobs ==="
if crontab -l 2>/dev/null | grep -q "dapmeet"; then
    pass "Cron jobs configured"
else
    warn "No dapmeet cron jobs found"
fi

echo ""
echo "=== Checking Scripts ==="
scripts=("backup_postgres.sh" "cleanup_processing.sh" "rotate_backend_logs.sh" "docker_cleanup.sh" "deploy.sh")
for s in "${scripts[@]}"; do
    if [ -x "/opt/dapmeet/scripts/$s" ]; then
        pass "Script executable: $s"
    else
        fail "Script missing/not executable: $s"
    fi
done

echo ""
echo "=== Docker Status ==="
docker ps -a 2>/dev/null || warn "Cannot list Docker containers"

echo ""
echo "=== .env File ==="
if [ -f "/opt/dapmeet/backend/.env" ]; then
    perms=$(stat -c %a /opt/dapmeet/backend/.env 2>/dev/null || stat -f %Lp /opt/dapmeet/backend/.env 2>/dev/null)
    if [ "$perms" = "600" ]; then
        pass ".env file exists with secure permissions (600)"
    else
        warn ".env file exists but permissions are $perms (should be 600)"
    fi
else
    warn ".env file not found at /opt/dapmeet/backend/.env"
fi

echo ""
echo "============================================="
echo "  Verification Complete"
echo "============================================="

