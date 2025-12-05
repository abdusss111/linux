#!/bin/bash
#==============================================================================
# Script: verify_vm1.sh
# Purpose: Verify SIS4 setup on VM1 (Frontend)
# Usage: sudo bash verify_vm1.sh
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
echo "  SIS4 Verification - VM1 (Frontend)"
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
if docker images | grep -q "abdusss111/dapmeet-client"; then
    IMAGE_TAG=$(docker images abdusss111/dapmeet-client --format "{{.Tag}}" | head -1)
    pass "Docker image present: abdusss111/dapmeet-client:$IMAGE_TAG"
else
    warn "Docker image abdusss111/dapmeet-client not found (will pull on first start)"
fi

#==============================================================================
# 2. Systemd Service Verification
#==============================================================================
echo ""
info "Checking systemd service..."

# Check if service file exists
if [ -f "/etc/systemd/system/dapmeet-frontend.service" ]; then
    pass "Systemd service file exists"
else
    fail "Systemd service file not found"
fi

# Check if service is enabled
if systemctl is-enabled --quiet dapmeet-frontend 2>/dev/null; then
    pass "dapmeet-frontend service is enabled"
else
    warn "dapmeet-frontend service is not enabled"
fi

# Check service configuration
if systemctl cat dapmeet-frontend 2>/dev/null | grep -q "Restart=always"; then
    pass "Service has auto-restart configured"
else
    warn "Service may not have auto-restart configured"
fi

# Check if service is running (optional)
if systemctl is-active --quiet dapmeet-frontend 2>/dev/null; then
    pass "dapmeet-frontend service is running"
    
    # Check container health if running
    if docker ps | grep -q "dapmeet-frontend"; then
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' dapmeet-frontend 2>/dev/null || echo "unknown")
        if [ "$HEALTH" = "healthy" ]; then
            pass "Container health check: healthy"
        elif [ "$HEALTH" = "unknown" ]; then
            info "Container health check: not configured or unknown"
        else
            warn "Container health check: $HEALTH"
        fi
    fi
else
    info "dapmeet-frontend service is not running (start with: sudo systemctl start dapmeet-frontend)"
fi

#==============================================================================
# 3. Cron Jobs Verification
#==============================================================================
echo ""
info "Checking cron jobs..."

# Check if cron scripts exist
CRON_DIR="/opt/dapmeet/scripts/cron"

if [ -f "$CRON_DIR/backup_frontend_logs.sh" ]; then
    if [ -x "$CRON_DIR/backup_frontend_logs.sh" ]; then
        pass "backup_frontend_logs.sh exists and is executable"
    else
        fail "backup_frontend_logs.sh exists but is not executable"
    fi
else
    fail "backup_frontend_logs.sh not found"
fi

if [ -f "$CRON_DIR/check_ssl_renewal.sh" ]; then
    if [ -x "$CRON_DIR/check_ssl_renewal.sh" ]; then
        pass "check_ssl_renewal.sh exists and is executable"
    else
        fail "check_ssl_renewal.sh exists but is not executable"
    fi
else
    fail "check_ssl_renewal.sh not found"
fi

# Check crontab configuration
if [ -f "/etc/cron.d/dapmeet-frontend" ]; then
    pass "Crontab file exists: /etc/cron.d/dapmeet-frontend"
    
    # Verify cron entries
    if grep -q "backup_frontend_logs.sh" /etc/cron.d/dapmeet-frontend; then
        pass "Log backup cron job configured (Daily 2:00 AM)"
    else
        fail "Log backup cron job not found in crontab"
    fi
    
    if grep -q "check_ssl_renewal.sh" /etc/cron.d/dapmeet-frontend; then
        pass "SSL check cron job configured (Weekly Mon 6:00 AM)"
    else
        fail "SSL check cron job not found in crontab"
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
    "/var/backups/dapmeet/logs"
    "/opt/dapmeet/frontend"
    "/etc/dapmeet/ssl"
    "/etc/dapmeet/nginx"
)

for dir in "${DIRS_TO_CHECK[@]}"; do
    if [ -d "$dir" ]; then
        pass "Directory exists: $dir"
    else
        warn "Directory missing: $dir"
    fi
done

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


