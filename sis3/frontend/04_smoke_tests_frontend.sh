#!/bin/bash
# ===========================================
# VM1 (Frontend) - Smoke Tests
# ===========================================
set -e

echo "[VM1 TEST] Starting Nginx..."
sudo systemctl start nginx

echo "[VM1 TEST] Checking HTTP response..."
curl -I http://localhost | grep "200 OK" && echo "Frontend OK"

echo "[VM1] Frontend smoke test completed successfully!"
