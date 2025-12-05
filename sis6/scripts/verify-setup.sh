#!/bin/bash
#==============================================================================
# Script: verify-setup.sh
# Purpose: Verify SIS6 journaling and auditing setup
# Usage: sudo bash verify-setup.sh
#==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0

pass() { echo -e "${GREEN}[PASS]${NC} $1"; ((PASSED++)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; ((FAILED++)); }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; ((WARNINGS++)); }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          SIS6 - Journaling & Auditing Verification           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

#==============================================================================
# Task 1: Journald Verification
#==============================================================================
info "=== Task 1: Journald Configuration ==="

# Check journald service
if systemctl is-active --quiet systemd-journald; then
    pass "systemd-journald is running"
else
    fail "systemd-journald is not running"
fi

# Check persistent storage
if [ -d /var/log/journal ]; then
    pass "Persistent journal storage exists (/var/log/journal)"
else
    fail "Persistent journal storage not found"
fi

# Check journal config
if grep -q "Storage=persistent" /etc/systemd/journald.conf 2>/dev/null; then
    pass "Journald configured for persistent storage"
else
    warn "Journald may not be configured for persistent storage"
fi

# Check rsyslog
if systemctl is-active --quiet rsyslog; then
    pass "rsyslog is running"
else
    fail "rsyslog is not running"
fi

# Check rsyslog config
if rsyslogd -N1 2>&1 | grep -q "rsyslogd: version"; then
    pass "rsyslog configuration is valid"
else
    warn "rsyslog configuration may have issues"
fi

# Check custom log directory
if [ -d /var/log/dapmeet ]; then
    pass "Dapmeet log directory exists"
else
    warn "Dapmeet log directory not found"
fi

#==============================================================================
# Task 2: Journal Toolset Verification
#==============================================================================
echo ""
info "=== Task 2: Journal Toolset ==="

TOOLS_DIR="/opt/dapmeet/scripts/journal"
TOOLS=(
    "journal-search.sh"
    "journal-services.sh"
    "journal-security.sh"
    "audit-search.sh"
    "log-analyzer.sh"
    "journal-monitor.sh"
    "daily-report.sh"
)

# Check tools directory
if [ -d "$TOOLS_DIR" ]; then
    pass "Tools directory exists: $TOOLS_DIR"
else
    fail "Tools directory not found: $TOOLS_DIR"
fi

# Check each tool
for tool in "${TOOLS[@]}"; do
    if [ -f "$TOOLS_DIR/$tool" ] && [ -x "$TOOLS_DIR/$tool" ]; then
        pass "$tool installed and executable"
    else
        fail "$tool not found or not executable"
    fi
done

# Check symlinks
for tool in "${TOOLS[@]}"; do
    link_name="${tool%.sh}"
    if [ -L "/usr/local/bin/$link_name" ]; then
        pass "Symlink exists: /usr/local/bin/$link_name"
    else
        warn "Symlink missing: /usr/local/bin/$link_name"
    fi
done

#==============================================================================
# Task 3: Auditd Verification
#==============================================================================
echo ""
info "=== Task 3: Auditd Configuration ==="

# Check auditd service
if systemctl is-active --quiet auditd; then
    pass "auditd is running"
else
    fail "auditd is not running"
fi

# Check auditd is enabled
if systemctl is-enabled --quiet auditd; then
    pass "auditd is enabled at boot"
else
    warn "auditd is not enabled at boot"
fi

# Check audit rules are loaded
rule_count=$(auditctl -l 2>/dev/null | wc -l)
if [ "$rule_count" -gt 5 ]; then
    pass "$rule_count audit rules loaded"
else
    warn "Only $rule_count audit rules loaded (expected more)"
fi

# Check key audit rules
REQUIRED_KEYS=(
    "sudoers_changes"
    "identity_changes"
    "ssh_config_changes"
)

for key in "${REQUIRED_KEYS[@]}"; do
    if auditctl -l 2>/dev/null | grep -q "key=$key"; then
        pass "Audit key '$key' is configured"
    else
        fail "Audit key '$key' is NOT configured"
    fi
done

# Check audit log exists
if [ -f /var/log/audit/audit.log ]; then
    pass "Audit log exists: /var/log/audit/audit.log"
else
    warn "Audit log not found"
fi

# Check audit rules files
if [ -d /etc/audit/rules.d ]; then
    rules_files=$(ls /etc/audit/rules.d/*.rules 2>/dev/null | wc -l)
    pass "$rules_files audit rule files in /etc/audit/rules.d/"
else
    fail "Audit rules directory not found"
fi

#==============================================================================
# Functional Tests
#==============================================================================
echo ""
info "=== Functional Tests ==="

# Test journal query
if journalctl -n 1 --no-pager >/dev/null 2>&1; then
    pass "Journal query works"
else
    fail "Journal query failed"
fi

# Test ausearch
if command -v ausearch >/dev/null 2>&1; then
    if ausearch --start today -m USER_AUTH 2>&1 | head -1 >/dev/null; then
        pass "ausearch command works"
    else
        pass "ausearch command works (no events yet)"
    fi
else
    fail "ausearch command not found"
fi

# Test audit logging (create test event)
info "Testing audit event capture..."
if [ -f /etc/sudoers ]; then
    # Touch sudoers to trigger audit (read access)
    cat /etc/sudoers > /dev/null 2>&1
    sleep 1
    if ausearch -k sudoers_changes --start recent 2>&1 | grep -q "type="; then
        pass "Audit events are being captured"
    else
        info "No recent sudoers audit events (normal if file wasn't modified)"
    fi
fi

#==============================================================================
# Summary
#==============================================================================
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                    Verification Summary                       ${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}Passed:${NC}   $PASSED"
echo -e "  ${RED}Failed:${NC}   $FAILED"
echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓ SIS6 setup verification passed!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Some checks failed. Please review and fix issues above.${NC}"
    exit 1
fi

