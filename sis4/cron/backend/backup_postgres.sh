#!/bin/bash
#==============================================================================
# Script: backup_postgres.sh
# Purpose: Create daily PostgreSQL database backups
# Schedule: Daily at 3:00 AM
# VM: VM2 (Backend)
# Cron: 0 3 * * * /opt/dapmeet/scripts/cron/backup_postgres.sh
#==============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="/var/backups/dapmeet/postgresql"
DB_NAME="dapmeet"
DB_USER="postgres"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_$DATE.sql.gz"
RETENTION_DAYS=7
LOG_FILE="/var/log/dapmeet/postgres_backup.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Logging function
log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# Error handling
handle_error() {
    log "ERROR: Backup failed at line $1"
    # Remove incomplete backup if exists
    [ -f "$BACKUP_FILE" ] && rm -f "$BACKUP_FILE"
    exit 1
}
trap 'handle_error $LINENO' ERR

log "Starting PostgreSQL backup for database: $DB_NAME"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    log "ERROR: PostgreSQL service is not running"
    exit 1
fi

# Check database exists
if ! sudo -u $DB_USER psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    log "ERROR: Database $DB_NAME does not exist"
    exit 1
fi

# Get database size before backup
DB_SIZE=$(sudo -u $DB_USER psql -d $DB_NAME -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));")
log "Database size: $DB_SIZE"

# Create backup using pg_dump with compression
log "Creating backup: $BACKUP_FILE"
sudo -u $DB_USER pg_dump \
    --format=plain \
    --verbose \
    --no-owner \
    --no-privileges \
    "$DB_NAME" 2>> "$LOG_FILE" | gzip > "$BACKUP_FILE"

# Verify backup file was created and has content
if [ ! -s "$BACKUP_FILE" ]; then
    log "ERROR: Backup file is empty or was not created"
    exit 1
fi

# Set proper permissions
chown backup:postgres "$BACKUP_FILE"
chmod 640 "$BACKUP_FILE"

# Get backup file size
BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
log "Backup completed: $BACKUP_FILE (Size: $BACKUP_SIZE)"

# Verify backup integrity (quick check)
log "Verifying backup integrity..."
if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
    log "Backup integrity check: PASSED"
else
    log "WARNING: Backup integrity check failed"
fi

# Remove old backups
DELETED_COUNT=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
log "Removed $DELETED_COUNT backup(s) older than $RETENTION_DAYS days"

# Calculate total backup storage used
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" | wc -l)
log "Total backups: $BACKUP_COUNT, Total size: $TOTAL_SIZE"

log "PostgreSQL backup completed successfully"
exit 0


