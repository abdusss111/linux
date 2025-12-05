#!/bin/bash
set -e

echo "Waiting for database to be ready..."

# Try to connect to database (with retries)
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
  if python -c "
import os
import sys
from sqlalchemy import create_engine, text
try:
    # Try DATABASE_URL first, then DATABASE_URL_ASYNC
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        db_url_async = os.getenv('DATABASE_URL_ASYNC')
        if db_url_async:
            # Convert async URL to sync
            db_url = db_url_async.replace('+asyncpg', '').replace('postgresql+asyncpg://', 'postgresql://')
    if not db_url:
        sys.exit(1)
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
    echo "Database is ready!"
    break
  fi
  
  attempt=$((attempt + 1))
  echo "Waiting for database... (attempt $attempt/$max_attempts)"
  sleep 2
done

if [ $attempt -eq $max_attempts ]; then
  echo "ERROR: Database connection failed after $max_attempts attempts"
  exit 1
fi

echo "Running migrations..."
# Ensure we're in the app directory and alembic.ini exists
cd /app
if [ ! -f "alembic.ini" ]; then
  echo "ERROR: alembic.ini not found in /app directory"
  ls -la /app | head -10
  exit 1
fi
PYTHONPATH=/app/src alembic upgrade head

echo "Starting application..."
exec uvicorn dapmeet.cmd.main:app --host 0.0.0.0 --port 8000

