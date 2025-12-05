#!/bin/bash
#==============================================================================
# Script: verify_vm2.sh
# Purpose: Verify SIS4 setup on VM2 (Backend)
# Usage: sudo bash verify_vm2.sh
#==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Test functions
pass() { echo -e "${GREEN}[PASS]${NC} $1"; ((PASSED++)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; ((FAILED++)); }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; ((WARNINGS++)); }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

echo ""
echo "=============================================="
echo "  SIS4 Verification - VM2 (Backend)"
echo "=============================================="
echo ""

#==============================================================================
# 1. Docker Verification
#==============================================================================
info "Checking Docker installation..."

# Check if Docker is installed
if command -v docker &> /dev/null; then
    pass "Docker is installed: $(docker --version | head -1)"
else
    fail "Docker is not installed"
fi

# Check if Docker service is running
if systemctl is-active --quiet docker; then
    pass "Docker service is running"
else
    fail "Docker service is not running"
fi

# Check if Docker service is enabled
if systemctl is-enabled --quiet docker; then
    pass "Docker service is enabled on boot"
else
    warn "Docker service is not enabled on boot"
fi

# Check Docker image
if docker images | grep -q "abdusss111/dapmeet-service"; then
    IMAGE_TAG=$(docker images abdusss111/dapmeet-service --format "{{.Tag}}" | head -1)
    pass "Docker image present: abdusss111/dapmeet-service:$IMAGE_TAG"
else
    warn "Docker image abdusss111/dapmeet-service not found (will pull on first start)"
fi

#==============================================================================
# 2. Systemd Service Verification
#==============================================================================
echo ""
info "Checking systemd service..."

# Check if service file exists
if [ -f "/etc/systemd/system/dapmeet-backend.service" ]; then
    pass "Systemd service file exists"
else
    fail "Systemd service file not found"
fi

# Check if service is enabled
if systemctl is-enabled --quiet dapmeet-backend 2>/dev/null; then
    pass "dapmeet-backend service is enabled"
else
    warn "dapmeet-backend service is not enabled"
fi

# Check service configuration
if systemctl cat dapmeet-backend 2>/dev/null | grep -q "Restart=always"; then
    pass "Service has auto-restart configured"
else
    warn "Service may not have auto-restart configured"
fi

# Check if service is running (optional)
if systemctl is-active --quiet dapmeet-backend 2>/dev/null; then
    pass "dapmeet-backend service is running"
    
    # Check container health if running
    if docker ps | grep -q "dapmeet-backend"; then
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' dapmeet-backend 2>/dev/null || echo "unknown")
        if [ "$HEALTH" = "healthy" ]; then
            pass "Container health check: healthy"
        elif [ "$HEALTH" = "unknown" ]; then
            info "Container health check: not configured or unknown"
        else
            warn "Container health check: $HEALTH"
        fi
    fi
else
    info "dapmeet-backend service is not running (start with: sudo systemctl start dapmeet-backend)"
fi

#==============================================================================
# 3. Cron Jobs Verification
#==============================================================================
echo ""
info "Checking cron jobs..."

# Check if cron scripts exist
CRON_DIR="/opt/dapmeet/scripts/cron"

CRON_SCRIPTS=(
    "backup_postgres.sh"
    "cleanup_processing.sh"
    "rotate_backend_logs.sh"
)

for script in "${CRON_SCRIPTS[@]}"; do
    if [ -f "$CRON_DIR/$script" ]; then
        if [ -x "$CRON_DIR/$script" ]; then
            pass "$script exists and is executable"
        else
            fail "$script exists but is not executable"
        fi
    else
        fail "$script not found"
    fi
done

# Check crontab configuration
if [ -f "/etc/cron.d/dapmeet-backend" ]; then
    pass "Crontab file exists: /etc/cron.d/dapmeet-backend"
    
    # Verify cron entries
    if grep -q "backup_postgres.sh" /etc/cron.d/dapmeet-backend; then
        pass "PostgreSQL backup cron job configured (Daily 3:00 AM)"
    else
        fail "PostgreSQL backup cron job not found in crontab"
    fi
    
    if grep -q "cleanup_processing.sh" /etc/cron.d/dapmeet-backend; then
        pass "Cleanup cron job configured (Daily 4:30 AM)"
    else
        fail "Cleanup cron job not found in crontab"
    fi
    
    if grep -q "rotate_backend_logs.sh" /etc/cron.d/dapmeet-backend; then
        pass "Log rotation cron job configured (Weekly Sun 5:00 AM)"
    else
        fail "Log rotation cron job not found in crontab"
    fi
else
    fail "Crontab file not found"
fi

# Check if cron service is running
if systemctl is-active --quiet cron 2>/dev/null || systemctl is-active --quiet crond 2>/dev/null; then
    pass "Cron service is running"
else
    warn "Cron service may not be running"
fi

#==============================================================================
# 4. Directory Structure Verification
#==============================================================================
echo ""
info "Checking directory structure..."

DIRS_TO_CHECK=(
    "/var/log/dapmeet"
    "/var/backups/dapmeet/postgresql"
    "/var/backups/dapmeet/logs"
    "/var/dapmeet/processing"
    "/var/dapmeet/uploads"
    "/opt/dapmeet/backend"
    "/etc/dapmeet/backend"
)

for dir in "${DIRS_TO_CHECK[@]}"; do
    if [ -d "$dir" ]; then
        pass "Directory exists: $dir"
    else
        warn "Directory missing: $dir"
    fi
done

#==============================================================================
# 5. PostgreSQL Verification (for backup script)
#==============================================================================
echo ""
info "Checking PostgreSQL (required for backup)..."

if command -v psql &> /dev/null; then
    pass "PostgreSQL client is installed"
else
    warn "PostgreSQL client not found (required for backup_postgres.sh)"
fi

if systemctl is-active --quiet postgresql 2>/dev/null; then
    pass "PostgreSQL service is running"
    
    # Check if dapmeet database exists
    if sudo -u postgres psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "dapmeet"; then
        pass "Database 'dapmeet' exists"
    else
        warn "Database 'dapmeet' not found (backup script requires it)"
    fi
else
    warn "PostgreSQL service is not running"
fi

#==============================================================================
# 6. Logrotate Verification
#==============================================================================
echo ""
info "Checking logrotate..."

if command -v logrotate &> /dev/null; then
    pass "Logrotate is installed"
else
    warn "Logrotate not found (required for rotate_backend_logs.sh)"
fi

#==============================================================================
# Summary
#==============================================================================
echo ""
echo "=============================================="
echo "  Verification Summary"
echo "=============================================="
echo -e "  ${GREEN}Passed:${NC}   $PASSED"
echo -e "  ${RED}Failed:${NC}   $FAILED"
echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
echo "=============================================="

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All critical checks passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some checks failed. Please review and fix issues above.${NC}"
    exit 1
fi


