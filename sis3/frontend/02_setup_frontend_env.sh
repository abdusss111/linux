#!/bin/bash
# ===========================================
# VM1 (Frontend) - Setup Next.js environment
# ===========================================
set -e

FRONT_DIR="/opt/dapmeet/frontend"

echo "[VM1] Installing Node dependencies..."
cd $FRONT_DIR
npm install next react axios shadcn-ui dotenv

echo "[VM1] Building production frontend..."
npm run build

echo "[VM1] Frontend compiled successfully at $FRONT_DIR/.next"
