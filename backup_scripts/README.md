# AIT CMMS Backup Scripts

This folder contains automated backup and restore scripts for your AIT CMMS PostgreSQL database.

---

## FILES

### Backup Scripts
- **`backup_daily.sh`** - Linux/macOS daily backup script
- **`backup_daily.bat`** - Windows daily backup script

### Restore Scripts
- **`restore_backup.sh`** - Linux/macOS restore script
- **`restore_backup.bat`** - Windows restore script

---

## SETUP INSTRUCTIONS

### 1. Configure Backup Scripts

**Linux/macOS:**
```bash
# Edit the script
nano backup_daily.sh

# Change these lines:
export PGPASSWORD='your_postgres_password'  # Set your actual password
BACKUP_DIR="/home/user/AIT_CMMS2.3.1/database_backups"  # Adjust path if needed

# Make executable
chmod +x backup_daily.sh
```

**Windows:**
```cmd
# Edit backup_daily.bat in Notepad
# Change these lines:
set PGPASSWORD=your_postgres_password
set BACKUP_DIR=C:\CMMS_Backups
```

### 2. Test Backup Script

**Linux/macOS:**
```bash
./backup_daily.sh
```

**Windows:**
```cmd
backup_daily.bat
```

Check that a .dump file was created in the backup directory.

### 3. Schedule Automated Backups

**Linux/macOS - Using Cron:**
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 2:00 AM)
0 2 * * * /home/user/AIT_CMMS2.3.1/backup_scripts/backup_daily.sh

# Save and exit
```

**Windows - Using Task Scheduler:**
1. Open Task Scheduler (taskschd.msc)
2. Click "Create Basic Task"
3. Name: "CMMS Daily Backup"
4. Trigger: Daily
5. Time: 2:00 AM
6. Action: Start a program
7. Program/script: Browse to `backup_daily.bat`
8. Click Finish

---

## USING RESTORE SCRIPTS

### Linux/macOS

**List available backups:**
```bash
ls -lh /home/user/AIT_CMMS2.3.1/database_backups/
```

**Restore a backup:**
```bash
./restore_backup.sh /home/user/AIT_CMMS2.3.1/database_backups/ait_cmms_backup_20260116_140530.dump
```

### Windows

**List available backups:**
```cmd
dir C:\CMMS_Backups\*.dump
```

**Restore a backup:**
```cmd
restore_backup.bat C:\CMMS_Backups\ait_cmms_backup_20260116_140530.dump
```

---

## BACKUP RETENTION

By default, backups older than **30 days** are automatically deleted to save disk space.

To change retention period:
- Edit the script
- Change `RETENTION_DAYS=30` to your desired number of days

---

## BACKUP FILE NAMING

Backup files are named with timestamp:
```
ait_cmms_backup_YYYYMMDD_HHMMSS.dump
```

Example:
```
ait_cmms_backup_20260116_140530.dump
```
- Created on: 2026-01-16 at 14:05:30

---

## TROUBLESHOOTING

### "Permission denied" error
**Linux/macOS:**
```bash
chmod +x backup_daily.sh
chmod +x restore_backup.sh
```

### "pg_dump not found" error
Add PostgreSQL bin directory to PATH:

**Linux/macOS:**
```bash
export PATH=$PATH:/usr/lib/postgresql/18/bin
```

**Windows:**
Add to System PATH: `C:\Program Files\PostgreSQL\18\bin`

### Backup file is 0 bytes
- Check PostgreSQL password in script
- Verify database name is correct
- Check PostgreSQL is running
- Review log file in backup directory

### Restore fails with permission errors
Run restore as postgres user:
```bash
# Edit restore script
# Change: DB_USER="cmms_user"
# To: DB_USER="postgres"
```

---

## MONITORING BACKUPS

### Check last backup
**Linux/macOS:**
```bash
ls -lt /home/user/AIT_CMMS2.3.1/database_backups/ | head
```

**Windows:**
```cmd
dir /O-D C:\CMMS_Backups\*.dump
```

### View backup logs
**Linux/macOS:**
```bash
tail -50 /home/user/AIT_CMMS2.3.1/database_backups/backup_log_*.txt
```

**Windows:**
```cmd
type C:\CMMS_Backups\backup_log_*.txt
```

### Verify backup integrity
```bash
# Connect to database
psql -U cmms_user -h localhost -d ait_cmms

# Check record counts
SELECT 'equipment', COUNT(*) FROM equipment
UNION ALL SELECT 'users', COUNT(*) FROM users;

# Exit
\q
```

---

## OFF-SITE BACKUP RECOMMENDATIONS

**CRITICAL:** Store backups in multiple locations!

### Option 1: Cloud Sync
Configure your backup directory to sync with:
- Google Drive
- OneDrive
- Dropbox
- iCloud

### Option 2: Network Storage (NAS)
**Linux/macOS - Add to backup script:**
```bash
# Add at end of backup_daily.sh
rsync -avz "$BACKUP_DIR/" /mnt/nas/CMMS_Backups/
```

**Windows - Add to backup script:**
```cmd
REM Add at end of backup_daily.bat
robocopy "%BACKUP_DIR%" "\\NAS\CMMS_Backups" *.dump /E /COPY:DAT
```

### Option 3: External Drive
- Keep external USB drive connected
- Set backup directory to external drive
- Rotate drives weekly for extra safety

---

## EMERGENCY RESTORE PROCEDURE

If the database becomes corrupted:

1. **Stop the application**
   - Close all CMMS windows on all computers

2. **Identify the latest good backup**
   ```bash
   ls -lt /home/user/AIT_CMMS2.3.1/database_backups/
   ```

3. **Drop the corrupted database**
   ```bash
   psql -U postgres -h localhost
   ```
   ```sql
   DROP DATABASE ait_cmms;
   CREATE DATABASE ait_cmms;
   GRANT ALL PRIVILEGES ON DATABASE ait_cmms TO cmms_user;
   \c ait_cmms
   GRANT ALL ON SCHEMA public TO cmms_user;
   \q
   ```

4. **Restore from backup**
   ```bash
   ./restore_backup.sh /path/to/backup.dump
   ```

5. **Verify data**
   ```bash
   psql -U cmms_user -h localhost -d ait_cmms
   ```
   ```sql
   \dt
   SELECT COUNT(*) FROM equipment;
   \q
   ```

6. **Restart application**
   ```bash
   python AIT_CMMS_REV3.py
   ```

---

## BACKUP CHECKLIST

Daily:
- [ ] Verify backup script ran successfully
- [ ] Check backup file was created with reasonable size

Weekly:
- [ ] Review backup logs for errors
- [ ] Verify off-site backup is syncing
- [ ] Check disk space in backup directory

Monthly:
- [ ] Test restore procedure with old backup
- [ ] Review retention policy
- [ ] Clean up very old backup logs

---

## SUPPORT

For detailed migration instructions, see:
- `../MIGRATION_GUIDE_NEON_TO_LOCAL_POSTGRESQL.md`
- `../QUICK_START_MIGRATION.md`

For PostgreSQL help:
- Documentation: https://www.postgresql.org/docs/18/
- Check logs:
  - Windows: `C:\Program Files\PostgreSQL\18\data\log\`
  - Linux: `/var/log/postgresql/`

---

**Remember:** You are now responsible for database backups!
NEON's automatic backups are gone. Make sure these scripts run daily.
