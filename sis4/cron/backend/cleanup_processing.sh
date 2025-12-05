#!/bin/bash
#==============================================================================
# Script: cleanup_processing.sh
# Purpose: Clean up old transcription processing files
# Schedule: Daily at 4:30 AM
# VM: VM2 (Backend)
# Cron: 30 4 * * * /opt/dapmeet/scripts/cron/cleanup_processing.sh
#==============================================================================

set -euo pipefail

# Configuration
PROCESSING_DIR="/var/dapmeet/processing"
TEMP_DIR="/tmp/dapmeet-setup"
UPLOAD_DIR="/var/dapmeet/uploads"
DAYS_OLD=3
LOG_FILE="/var/log/dapmeet/cleanup.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Logging function
log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

log "Starting processing cleanup..."

# Track cleanup statistics
TOTAL_FILES_DELETED=0
TOTAL_DIRS_DELETED=0
TOTAL_SPACE_FREED=0

# Function to cleanup a directory
cleanup_directory() {
    local dir=$1
    local days=$2
    local description=$3
    
    if [ ! -d "$dir" ]; then
        log "Directory $dir does not exist, skipping"
        return
    fi
    
    # Calculate space before cleanup
    local space_before=$(du -sb "$dir" 2>/dev/null | cut -f1)
    
    # Remove old files
    local files_deleted=$(find "$dir" -type f -mtime +$days -delete -print 2>/dev/null | wc -l)
    TOTAL_FILES_DELETED=$((TOTAL_FILES_DELETED + files_deleted))
    
    # Remove empty directories
    local dirs_deleted=$(find "$dir" -type d -empty -delete -print 2>/dev/null | wc -l)
    TOTAL_DIRS_DELETED=$((TOTAL_DIRS_DELETED + dirs_deleted))
    
    # Calculate space after cleanup
    local space_after=$(du -sb "$dir" 2>/dev/null | cut -f1)
    local space_freed=$((space_before - space_after))
    TOTAL_SPACE_FREED=$((TOTAL_SPACE_FREED + space_freed))
    
    log "$description: Removed $files_deleted files, $dirs_deleted directories"
}

# Clean processing directory (transcription temporary files)
cleanup_directory "$PROCESSING_DIR" $DAYS_OLD "Processing files"

# Clean temporary setup files
cleanup_directory "$TEMP_DIR" 1 "Temporary setup files"

# Clean old uploads (if they weren't processed)
if [ -d "$UPLOAD_DIR" ]; then
    cleanup_directory "$UPLOAD_DIR" 7 "Old uploads"
fi

# Clean Docker-related temporary files
if [ -d "/var/lib/docker/tmp" ]; then
    log "Cleaning Docker temporary files..."
    find /var/lib/docker/tmp -type f -mtime +1 -delete 2>/dev/null || true
fi

# Clean old log files in /tmp
TMP_LOGS_DELETED=$(find /tmp -name "*.log" -mtime +7 -delete -print 2>/dev/null | wc -l)
log "Cleaned $TMP_LOGS_DELETED old log files from /tmp"

# Convert bytes to human readable
if [ $TOTAL_SPACE_FREED -gt 0 ]; then
    SPACE_FREED_HR=$(numfmt --to=iec $TOTAL_SPACE_FREED 2>/dev/null || echo "${TOTAL_SPACE_FREED} bytes")
else
    SPACE_FREED_HR="0 bytes"
fi

# Summary
log "=== Cleanup Summary ==="
log "Total files deleted: $TOTAL_FILES_DELETED"
log "Total directories deleted: $TOTAL_DIRS_DELETED"
log "Total space freed: $SPACE_FREED_HR"
log "Processing cleanup completed"

exit 0


