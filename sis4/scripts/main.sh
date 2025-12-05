#!/bin/bash
#==============================================================================
# Script: main.sh
# Purpose: Interactive menu for SIS4 setup and verification
# Usage: sudo bash main.sh
#==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Please run as root: sudo bash $0${NC}"
        exit 1
    fi
}

# Print header
print_header() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║     ██████   █████  ██████  ███    ███ ███████ ███████ ████████ ║"
    echo "║     ██   ██ ██   ██ ██   ██ ████  ████ ██      ██         ██    ║"
    echo "║     ██   ██ ███████ ██████  ██ ████ ██ █████   █████      ██    ║"
    echo "║     ██   ██ ██   ██ ██      ██  ██  ██ ██      ██         ██    ║"
    echo "║     ██████  ██   ██ ██      ██      ██ ███████ ███████    ██    ║"
    echo "║                                                              ║"
    echo "║                   SIS4 - Setup & Management                  ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Print menu
print_menu() {
    echo -e "${BLUE}Select an option:${NC}"
    echo ""
    echo "  ${GREEN}Setup${NC}"
    echo "    1) Setup VM1 (Frontend)"
    echo "    2) Setup VM2 (Backend)"
    echo ""
    echo "  ${YELLOW}Verification${NC}"
    echo "    3) Verify VM1 setup"
    echo "    4) Verify VM2 setup"
    echo ""
    echo "  ${CYAN}Service Management${NC}"
    echo "    5) Start dapmeet-frontend service"
    echo "    6) Start dapmeet-backend service"
    echo "    7) Stop all services"
    echo "    8) View service status"
    echo ""
    echo "  ${RED}Exit${NC}"
    echo "    0) Exit"
    echo ""
}

# Execute choice
execute_choice() {
    case $1 in
        1)
            echo -e "\n${GREEN}Running VM1 (Frontend) setup...${NC}\n"
            bash "$SCRIPT_DIR/setup_vm1.sh"
            ;;
        2)
            echo -e "\n${GREEN}Running VM2 (Backend) setup...${NC}\n"
            bash "$SCRIPT_DIR/setup_vm2.sh"
            ;;
        3)
            echo -e "\n${GREEN}Verifying VM1 setup...${NC}\n"
            bash "$SCRIPT_DIR/verify_vm1.sh"
            ;;
        4)
            echo -e "\n${GREEN}Verifying VM2 setup...${NC}\n"
            bash "$SCRIPT_DIR/verify_vm2.sh"
            ;;
        5)
            echo -e "\n${GREEN}Starting dapmeet-frontend service...${NC}\n"
            systemctl start dapmeet-frontend && echo -e "${GREEN}Service started${NC}" || echo -e "${RED}Failed to start service${NC}"
            systemctl status dapmeet-frontend --no-pager
            ;;
        6)
            echo -e "\n${GREEN}Starting dapmeet-backend service...${NC}\n"
            systemctl start dapmeet-backend && echo -e "${GREEN}Service started${NC}" || echo -e "${RED}Failed to start service${NC}"
            systemctl status dapmeet-backend --no-pager
            ;;
        7)
            echo -e "\n${YELLOW}Stopping all dapmeet services...${NC}\n"
            systemctl stop dapmeet-frontend 2>/dev/null && echo "Stopped dapmeet-frontend" || echo "dapmeet-frontend not running"
            systemctl stop dapmeet-backend 2>/dev/null && echo "Stopped dapmeet-backend" || echo "dapmeet-backend not running"
            ;;
        8)
            echo -e "\n${BLUE}Service Status:${NC}\n"
            echo -e "${CYAN}=== dapmeet-frontend ===${NC}"
            systemctl status dapmeet-frontend --no-pager 2>/dev/null || echo "Not installed"
            echo ""
            echo -e "${CYAN}=== dapmeet-backend ===${NC}"
            systemctl status dapmeet-backend --no-pager 2>/dev/null || echo "Not installed"
            ;;
        0)
            echo -e "\n${GREEN}Goodbye!${NC}\n"
            exit 0
            ;;
        *)
            echo -e "\n${RED}Invalid option. Please try again.${NC}\n"
            ;;
    esac
}

# Main loop
main() {
    check_root
    
    while true; do
        print_header
        print_menu
        
        read -p "Enter your choice [0-8]: " choice
        execute_choice "$choice"
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

main


