#!/bin/bash
################################################################################
# AIT CMMS Restore Backup Script (Linux/macOS)
#
# This script restores a PostgreSQL database from a backup file
#
# Usage:
#   ./restore_backup.sh backup_file.dump
#
# Example:
#   ./restore_backup.sh /home/user/CMMS_Backups/ait_cmms_backup_20260116_140530.dump
################################################################################

# ============================================================================
# CONFIGURATION - EDIT THESE VALUES
# ============================================================================
export PGPASSWORD='your_postgres_password'  # Change this!
DB_NAME="ait_cmms"
DB_USER="cmms_user"
DB_HOST="localhost"
DB_PORT="5432"

# ============================================================================
# SCRIPT START
# ============================================================================

# Check if backup file is provided
if [ -z "$1" ]; then
    echo "ERROR: No backup file specified"
    echo ""
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 /home/user/CMMS_Backups/ait_cmms_backup_20260116_140530.dump"
    echo ""
    echo "Available backups:"
    ls -lh /home/user/AIT_CMMS2.3.1/database_backups/*.dump 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "========================================="
echo "AIT CMMS Database Restore"
echo "========================================="
echo "Backup file: $BACKUP_FILE"
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo ""

# Get file size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup size: $BACKUP_SIZE"
echo ""

# Confirm restore
read -p "WARNING: This will OVERWRITE the existing database. Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting restore process..."
echo ""

# Optional: Drop and recreate database (uncomment if needed)
# echo "Dropping existing database..."
# dropdb -U postgres -h $DB_HOST -p $DB_PORT $DB_NAME
# echo "Creating new database..."
# createdb -U postgres -h $DB_HOST -p $DB_PORT $DB_NAME
# psql -U postgres -h $DB_HOST -p $DB_PORT -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# Restore database
echo "Restoring database from backup..."
if pg_restore -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" --verbose --clean --if-exists "$BACKUP_FILE"; then
    echo ""
    echo "========================================="
    echo "Restore completed successfully!"
    echo "========================================="

    # Verify data
    echo ""
    echo "Verifying restored data..."
    psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -c "
        SELECT 'equipment' as table_name, COUNT(*) as record_count FROM equipment
        UNION ALL
        SELECT 'users', COUNT(*) FROM users
        UNION ALL
        SELECT 'pm_completions', COUNT(*) FROM pm_completions
        UNION ALL
        SELECT 'corrective_maintenance', COUNT(*) FROM corrective_maintenance
        UNION ALL
        SELECT 'work_orders', COUNT(*) FROM work_orders;
    "

    echo ""
    echo "Restore process completed: $(date)"
else
    echo ""
    echo "========================================="
    echo "ERROR: Restore failed!"
    echo "========================================="
    echo "Check the error messages above for details"
    exit 1
fi

# Unset password variable for security
unset PGPASSWORD

exit 0
