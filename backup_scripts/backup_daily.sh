#!/bin/bash
################################################################################
# AIT CMMS Daily Backup Script (Linux/macOS)
#
# This script creates daily backups of the PostgreSQL database
# and removes backups older than 30 days
#
# Setup Instructions:
# 1. Edit the configuration variables below
# 2. Make executable: chmod +x backup_daily.sh
# 3. Add to crontab: crontab -e
#    Add line: 0 2 * * * /home/user/AIT_CMMS2.3.1/backup_scripts/backup_daily.sh
################################################################################

# ============================================================================
# CONFIGURATION - EDIT THESE VALUES
# ============================================================================
export PGPASSWORD='your_postgres_password'  # Change this!
BACKUP_DIR="/home/user/AIT_CMMS2.3.1/database_backups"
DB_NAME="ait_cmms"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"
RETENTION_DAYS=30  # Keep backups for 30 days

# ============================================================================
# SCRIPT START - DO NOT EDIT BELOW THIS LINE
# ============================================================================

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_ONLY=$(date +%Y-%m-%d)

# Backup file names
BACKUP_FILE="$BACKUP_DIR/ait_cmms_backup_$TIMESTAMP.dump"
LOG_FILE="$BACKUP_DIR/backup_log_$DATE_ONLY.txt"

# Start backup
echo "========================================" >> "$LOG_FILE"
echo "Backup started: $(date)" >> "$LOG_FILE"
echo "Database: $DB_NAME" >> "$LOG_FILE"
echo "Host: $DB_HOST:$DB_PORT" >> "$LOG_FILE"

# Create backup using pg_dump
if pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -F c -f "$BACKUP_FILE" 2>> "$LOG_FILE"; then
    # Get backup file size
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

    echo "Backup completed successfully!" >> "$LOG_FILE"
    echo "File: $BACKUP_FILE" >> "$LOG_FILE"
    echo "Size: $BACKUP_SIZE" >> "$LOG_FILE"

    # Remove old backups
    echo "Removing backups older than $RETENTION_DAYS days..." >> "$LOG_FILE"
    find "$BACKUP_DIR" -name "*.dump" -mtime +$RETENTION_DAYS -delete

    # Count remaining backups
    BACKUP_COUNT=$(find "$BACKUP_DIR" -name "*.dump" | wc -l)
    echo "Total backups retained: $BACKUP_COUNT" >> "$LOG_FILE"

    echo "Backup process completed: $(date)" >> "$LOG_FILE"
    echo "Status: SUCCESS" >> "$LOG_FILE"
else
    echo "ERROR: Backup failed!" >> "$LOG_FILE"
    echo "Status: FAILED" >> "$LOG_FILE"
    echo "Check PostgreSQL logs for details" >> "$LOG_FILE"
    exit 1
fi

echo "========================================" >> "$LOG_FILE"

# Unset password variable for security
unset PGPASSWORD

# Optional: Send notification (uncomment to enable)
# echo "CMMS backup completed: $BACKUP_SIZE" | mail -s "Database Backup Success" admin@example.com

exit 0
