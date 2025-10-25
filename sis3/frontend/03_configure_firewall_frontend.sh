#!/bin/bash
# ===========================================
# VM1 (Frontend) - Configure firewall rules
# ===========================================
set -e

echo "[VM1] Setting up firewall for Frontend..."
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

sudo ufw status verbose
echo "[VM1] Firewall configured successfully!"
