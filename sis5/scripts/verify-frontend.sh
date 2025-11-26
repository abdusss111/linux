#!/bin/bash
#===============================================================================
# Dapmeet Frontend VM Verification Script
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
echo "  Dapmeet Frontend VM Verification"
echo "============================================="
echo ""

# Check groups
echo "=== Checking Groups ==="
groups=("dapmeet" "devops" "automation" "monitoring" "auditor" "sysadmin" "deployer" "docker")
for g in "${groups[@]}"; do
    if getent group "$g" > /dev/null 2>&1; then
        pass "Group exists: $g"
    else
        fail "Group missing: $g"
    fi
done

echo ""
echo "=== Checking Users ==="
users=("deployer" "sysadmin" "devops_user" "automation" "monitoring" "auditor")
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
    "/opt/dapmeet/frontend"
    "/opt/dapmeet/scripts"
    "/var/log/dapmeet"
    "/var/www/dapmeet/static"
    "/etc/dapmeet/nginx"
    "/etc/dapmeet/ssl"
    "/var/backups/dapmeet"
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
sudoers=("devops" "deployer" "monitoring" "automation")
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

# Docker
if systemctl is-active --quiet docker; then
    pass "Docker is running"
else
    fail "Docker is not running"
fi

# Nginx
if systemctl is-active --quiet nginx; then
    pass "Nginx is running"
else
    fail "Nginx is not running"
fi

# Dapmeet Frontend
if systemctl is-enabled --quiet dapmeet-frontend 2>/dev/null; then
    pass "dapmeet-frontend service is enabled"
    if systemctl is-active --quiet dapmeet-frontend; then
        pass "dapmeet-frontend service is running"
    else
        warn "dapmeet-frontend service is not running (may need image)"
    fi
else
    fail "dapmeet-frontend service not found"
fi

echo ""
echo "=== Checking Firewall ==="
if ufw status | grep -q "Status: active"; then
    pass "UFW is active"
    ufw status | grep -E "22|80|443" | while read line; do
        echo "     $line"
    done
else
    fail "UFW is not active"
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
scripts=("backup_frontend_logs.sh" "check_ssl_renewal.sh" "docker_cleanup.sh")
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
echo "============================================="
echo "  Verification Complete"
echo "============================================="

