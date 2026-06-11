#!/bin/bash
# Backup current database before re-ingestion

set -e  # Exit on error

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/linuxone_rag_${TIMESTAMP}.sql"

# Database connection details (from .env or defaults)
DB_USER="${POSTGRES_USER:-raguser}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_NAME="${POSTGRES_DB:-linuxone_rag}"

echo "========================================="
echo "Database Backup Script"
echo "========================================="
echo "Database: ${DB_NAME}"
echo "User: ${DB_USER}"
echo "Host: ${DB_HOST}"
echo "Backup file: ${BACKUP_FILE}"
echo "========================================="

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Backup database
echo "Starting backup..."
pg_dump -U "${DB_USER}" -h "${DB_HOST}" "${DB_NAME}" > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "✓ Backup completed successfully!"
    echo "Backup saved to: ${BACKUP_FILE}"
    
    # Get backup file size
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "Backup size: ${BACKUP_SIZE}"
    
    # Count number of backups
    BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/*.sql 2>/dev/null | wc -l)
    echo "Total backups: ${BACKUP_COUNT}"
    
    echo ""
    echo "To restore this backup, run:"
    echo "  psql -U ${DB_USER} -h ${DB_HOST} ${DB_NAME} < ${BACKUP_FILE}"
else
    echo "✗ Backup failed!"
    exit 1
fi

echo "========================================="

# Made with Bob
