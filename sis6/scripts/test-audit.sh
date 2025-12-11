#!/bin/bash
#==============================================================================
# Script: test-audit.sh
# Purpose: Test audit rules by triggering monitored events
# Usage: sudo bash test-audit.sh
# WARNING: This script modifies system files for testing!
#==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║            Audit Rules Test Script                           ║${NC}"
echo -e "${CYAN}║  This script triggers audit events for testing               ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root${NC}"
    exit 1
fi

echo -e "${YELLOW}WARNING: This script will make temporary changes to test audit rules.${NC}"
echo -e "${YELLOW}Press Enter to continue or Ctrl+C to cancel...${NC}"
read

#==============================================================================
# Test 1: Sudoers Changes (Task 3 Primary Requirement)
#==============================================================================
echo ""
echo -e "${BLUE}Test 1: Sudoers Changes${NC}"
echo "----------------------------------------"

# Create a test file in sudoers.d
TEST_SUDOERS="/etc/sudoers.d/zzz-test-audit"
echo "# Test audit rule - safe to delete" > "$TEST_SUDOERS"
chmod 440 "$TEST_SUDOERS"
echo -e "${GREEN}Created test sudoers file${NC}"

sleep 1

# Check for audit event
echo "Checking audit log..."
if ausearch -k sudoers_changes --start recent 2>/dev/null | grep -q "name=\"$TEST_SUDOERS\""; then
    echo -e "${GREEN}✓ Sudoers change was captured!${NC}"
else
    echo -e "${YELLOW}⚠ Event not found (may take a moment)${NC}"
fi

# Cleanup
rm -f "$TEST_SUDOERS"
echo "Cleaned up test file"

#==============================================================================
# Test 2: Identity Changes (passwd/group)
#==============================================================================
echo ""
echo -e "${BLUE}Test 2: Identity Changes${NC}"
echo "----------------------------------------"

# Create a test user
TEST_USER="testaudituser$$"
useradd -M -s /bin/false "$TEST_USER" 2>/dev/null || true
echo -e "${GREEN}Created test user: $TEST_USER${NC}"

sleep 1

# Check for audit event
if ausearch -k identity_changes --start recent 2>/dev/null | grep -q "useradd\|$TEST_USER"; then
    echo -e "${GREEN}✓ User creation was captured!${NC}"
else
    echo -e "${YELLOW}⚠ Event not found (may take a moment)${NC}"
fi

# Cleanup
userdel "$TEST_USER" 2>/dev/null || true
echo "Cleaned up test user"

#==============================================================================
# Test 3: Privileged Commands
#==============================================================================
echo ""
echo -e "${BLUE}Test 3: Privileged Commands${NC}"
echo "----------------------------------------"

# Run a privileged command
echo "Running passwd --status root..."
passwd --status root > /dev/null 2>&1 || true

sleep 1

# Check for audit event
if ausearch -k privileged_cmd --start recent 2>/dev/null | grep -q "passwd"; then
    echo -e "${GREEN}✓ Privileged command was captured!${NC}"
else
    echo -e "${YELLOW}⚠ Event not found (may take a moment)${NC}"
fi

#==============================================================================
# Test 4: SSH Config Changes
#==============================================================================
echo ""
echo -e "${BLUE}Test 4: SSH Config Changes${NC}"
echo "----------------------------------------"

if [ -f /etc/ssh/sshd_config ]; then
    # Just touch the file to trigger audit
    touch /etc/ssh/sshd_config
    echo -e "${GREEN}Touched sshd_config${NC}"
    
    sleep 1
    
    if ausearch -k ssh_config_changes --start recent 2>/dev/null | grep -q "sshd_config"; then
        echo -e "${GREEN}✓ SSH config access was captured!${NC}"
    else
        echo -e "${YELLOW}⚠ Event not found (may take a moment)${NC}"
    fi
else
    echo -e "${YELLOW}SSH config not found, skipping${NC}"
fi

#==============================================================================
# Summary
#==============================================================================
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                    Audit Test Complete                        ${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "View all recent audit events:"
echo -e "  ${YELLOW}ausearch --start recent${NC}"
echo ""
echo "Search by specific key:"
echo -e "  ${YELLOW}ausearch -k sudoers_changes --start today${NC}"
echo -e "  ${YELLOW}ausearch -k identity_changes --start today${NC}"
echo -e "  ${YELLOW}ausearch -k privileged_cmd --start today${NC}"
echo ""
echo "Generate audit report:"
echo -e "  ${YELLOW}aureport --summary${NC}"


