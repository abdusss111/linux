#!/bin/bash
#==============================================================================
# Script: check_ssl_renewal.sh
# Purpose: Check SSL certificate expiration and alert if renewal needed
# Schedule: Weekly on Mondays at 6:00 AM
# VM: VM1 (Frontend)
# Cron: 0 6 * * 1 /opt/dapmeet/scripts/cron/check_ssl_renewal.sh
#==============================================================================

set -euo pipefail

# Configuration
SSL_DIR="/etc/dapmeet/ssl"
CERT_FILE="$SSL_DIR/fullchain.pem"
DAYS_WARNING=30
DAYS_CRITICAL=7
LOG_FILE="/var/log/dapmeet/ssl_check.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Logging function
log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# Alert function (can be extended for email/slack notifications)
send_alert() {
    local level=$1
    local message=$2
    
    log "[$level] $message"
    
    # Add notification logic here:
    # - Email: mail -s "SSL Alert: $level" admin@example.com <<< "$message"
    # - Slack: curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"$message\"}" $SLACK_WEBHOOK
    
    # Write to syslog for monitoring systems
    logger -t "ssl-check" -p "user.$level" "$message"
}

log "Starting SSL certificate check..."

# Check if certificate exists
if [ ! -f "$CERT_FILE" ]; then
    send_alert "err" "SSL certificate not found at $CERT_FILE"
    exit 1
fi

# Get certificate expiration date
EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" 2>/dev/null | cut -d= -f2)

if [ -z "$EXPIRY_DATE" ]; then
    send_alert "err" "Failed to read SSL certificate expiration date"
    exit 1
fi

# Calculate days remaining
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null) || {
    # macOS compatibility
    EXPIRY_EPOCH=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$EXPIRY_DATE" +%s 2>/dev/null)
}
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

# Get certificate details
SUBJECT=$(openssl x509 -subject -noout -in "$CERT_FILE" | sed 's/subject=//')
ISSUER=$(openssl x509 -issuer -noout -in "$CERT_FILE" | sed 's/issuer=//')

log "Certificate: $SUBJECT"
log "Issuer: $ISSUER"
log "Expiry Date: $EXPIRY_DATE"
log "Days Remaining: $DAYS_LEFT"

# Check expiration status
if [ $DAYS_LEFT -lt 0 ]; then
    send_alert "crit" "SSL certificate has EXPIRED! Expired $((DAYS_LEFT * -1)) days ago."
    exit 2
elif [ $DAYS_LEFT -lt $DAYS_CRITICAL ]; then
    send_alert "crit" "CRITICAL: SSL certificate expires in $DAYS_LEFT days! Immediate renewal required."
    
    # Attempt automatic renewal with certbot if available
    if command -v certbot &> /dev/null; then
        log "Attempting automatic renewal with certbot..."
        certbot renew --quiet && log "Certificate renewed successfully" || log "Automatic renewal failed"
    fi
    exit 2
elif [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
    send_alert "warning" "WARNING: SSL certificate expires in $DAYS_LEFT days. Plan renewal soon."
    exit 1
else
    log "SSL certificate OK: $DAYS_LEFT days remaining until expiration"
    exit 0
fi


