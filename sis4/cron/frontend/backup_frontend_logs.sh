#!/bin/bash
#==============================================================================
# Script: backup_frontend_logs.sh
# Purpose: Backup frontend application and nginx logs
# Schedule: Daily at 2:00 AM
# VM: VM1 (Frontend)
# Cron: 0 2 * * * /opt/dapmeet/scripts/cron/backup_frontend_logs.sh
#==============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="/var/backups/dapmeet/logs"
LOG_DIRS=(
    "/var/log/dapmeet"
    "/var/log/nginx"
)
DATE=$(date +%Y%m%d)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
RETENTION_DAYS=30
LOG_FILE="/var/log/dapmeet/backup.log"

# Logging function
log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

log "Starting frontend logs backup..."

# Backup each log directory
for LOG_DIR in "${LOG_DIRS[@]}"; do
    if [ -d "$LOG_DIR" ]; then
        DIR_NAME=$(basename "$LOG_DIR")
        BACKUP_FILE="$BACKUP_DIR/${DIR_NAME}_logs_$DATE.tar.gz"
        
        # Create compressed backup
        tar -czf "$BACKUP_FILE" -C "$(dirname "$LOG_DIR")" "$DIR_NAME" 2>/dev/null || {
            log "Warning: Some files in $LOG_DIR could not be backed up"
        }
        
        # Set proper permissions
        chmod 640 "$BACKUP_FILE"
        chown backup:backup "$BACKUP_FILE" 2>/dev/null || true
        
        log "Backed up $LOG_DIR to $BACKUP_FILE"
    else
        log "Warning: Directory $LOG_DIR does not exist, skipping"
    fi
done

# Remove backups older than retention period
DELETED_COUNT=$(find "$BACKUP_DIR" -name "*_logs_*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
log "Removed $DELETED_COUNT backup(s) older than $RETENTION_DAYS days"

# Calculate total backup size
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
log "Frontend logs backup completed. Total backup size: $TOTAL_SIZE"

exit 0


