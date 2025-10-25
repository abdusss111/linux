#!/bin/bash
# ===========================================
# VM1 (Frontend) - Install base packages
# ===========================================
set -e

echo "[VM1] Updating system packages..."
sudo apt update && sudo apt upgrade -y

echo "[VM1] Installing required packages..."
sudo apt install -y nodejs npm nginx git ufw curl net-tools htop

echo "[VM1] Packages installed successfully on Frontend VM!"
