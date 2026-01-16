# QUICK START: NEON to Local PostgreSQL Migration

This is a simplified checklist for migrating your AIT CMMS from NEON to local PostgreSQL.
For detailed instructions, see `MIGRATION_GUIDE_NEON_TO_LOCAL_POSTGRESQL.md`.

---

## PHASE 1: SETUP POSTGRESQL (30 minutes)

### 1.1 Set PostgreSQL Password
```bash
# Connect to PostgreSQL
psql -U postgres

# Set password
ALTER USER postgres WITH PASSWORD 'AIT_CMMS_2024!';

# Exit
\q
```

### 1.2 Verify Port 5432
```bash
# Windows
netstat -ano | findstr :5432

# Linux
netstat -tuln | grep 5432
```

---

## PHASE 2: BACKUP NEON DATA (15 minutes)

### 2.1 Create Backup Directory
```bash
mkdir -p /home/user/AIT_CMMS2.3.1/database_backups
cd /home/user/AIT_CMMS2.3.1/database_backups
```

### 2.2 Backup NEON Database
```bash
pg_dump "postgresql://neondb_owner:npg_2Nm6hyPVWiIH@ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech:5432/neondb?sslmode=require" \
  --format=custom \
  --file=neon_backup_$(date +%Y%m%d_%H%M%S).dump
```

**Windows:**
```cmd
pg_dump "postgresql://neondb_owner:npg_2Nm6hyPVWiIH@ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech:5432/neondb?sslmode=require" --format=custom --file=neon_backup.dump
```

### 2.3 Verify Backup
```bash
ls -lh neon_backup*.dump  # Should show file size > 0
```

---

## PHASE 3: CONFIGURE POSTGRESQL FOR NETWORK ACCESS (20 minutes)

### 3.1 Get Your Laptop IP
```bash
# Windows
ipconfig

# Linux
hostname -I
```
**Note your IP (e.g., 192.168.1.100)**

### 3.2 Edit postgresql.conf

**Location:**
- Windows: `C:\Program Files\PostgreSQL\18\data\postgresql.conf`
- Linux: `/etc/postgresql/18/main/postgresql.conf`

**Change:**
```
listen_addresses = '*'
port = 5432
max_connections = 20
```

### 3.3 Edit pg_hba.conf

**Location:**
- Windows: `C:\Program Files\PostgreSQL\18\data\pg_hba.conf`
- Linux: `/etc/postgresql/18/main/pg_hba.conf`

**Add at bottom:**
```
# Local network access
host    all    all    192.168.1.0/24    scram-sha-256
```
(Adjust 192.168.1.0/24 to match your network)

### 3.4 Windows Firewall (Windows only)
```cmd
netsh advfirewall firewall add rule name="PostgreSQL" dir=in action=allow protocol=TCP localport=5432
```

### 3.5 Restart PostgreSQL
**Windows:** Services → postgresql-x64-18 → Restart
**Linux:** `sudo systemctl restart postgresql`

---

## PHASE 4: CREATE DATABASE & USER (10 minutes)

### 4.1 Create Database
```bash
psql -U postgres -h localhost
```

```sql
CREATE DATABASE ait_cmms;
CREATE USER cmms_user WITH PASSWORD 'CMMS_2024_Secure!';
GRANT ALL PRIVILEGES ON DATABASE ait_cmms TO cmms_user;
\c ait_cmms
GRANT ALL ON SCHEMA public TO cmms_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cmms_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cmms_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cmms_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cmms_user;
\q
```

---

## PHASE 5: UPDATE APPLICATION (5 minutes)

### 5.1 Edit AIT_CMMS_REV3.py (line 6820-6827)

**OLD:**
```python
self.DB_CONFIG = {
    'host': 'ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech',
    'port': 5432,
    'database': 'neondb',
    'user': 'neondb_owner',
    'password': 'npg_2Nm6hyPVWiIH',
    'sslmode': 'require'
}
```

**NEW:**
```python
self.DB_CONFIG = {
    'host': 'localhost',  # Or '192.168.1.100' for network access
    'port': 5432,
    'database': 'ait_cmms',
    'user': 'cmms_user',
    'password': 'CMMS_2024_Secure!',
    'sslmode': 'prefer'
}
```

### 5.2 Edit migrate_multiuser.py (line 256-263)

Make the **SAME** changes as above.

---

## PHASE 6: RESTORE DATA (15 minutes)

### 6.1 Restore from Backup
```bash
pg_restore --host=localhost \
           --port=5432 \
           --username=cmms_user \
           --dbname=ait_cmms \
           --verbose \
           neon_backup_YYYYMMDD_HHMMSS.dump
```

**Windows:**
```cmd
pg_restore --host=localhost --port=5432 --username=cmms_user --dbname=ait_cmms --verbose neon_backup.dump
```

### 6.2 Verify Data
```bash
psql -U cmms_user -h localhost -d ait_cmms
```

```sql
-- List tables
\dt

-- Count records
SELECT 'equipment', COUNT(*) FROM equipment
UNION ALL SELECT 'users', COUNT(*) FROM users;

\q
```

---

## PHASE 7: TEST (20 minutes)

### 7.1 Test Locally
```bash
cd /home/user/AIT_CMMS2.3.1
python AIT_CMMS_REV3.py
```

**Test:**
- [ ] Login works
- [ ] View equipment
- [ ] Create test PM completion
- [ ] View reports
- [ ] All modules load

### 7.2 Test from Another Computer
1. Update `DB_CONFIG` host to your laptop IP: `'192.168.1.100'`
2. Copy application to employee computer
3. Run application
4. Test login and basic functions

---

## PHASE 8: SETUP BACKUPS (15 minutes)

### 8.1 Configure Backup Script

**Linux/macOS:**
```bash
cd /home/user/AIT_CMMS2.3.1/backup_scripts
chmod +x backup_daily.sh
nano backup_daily.sh  # Edit password and paths
```

**Windows:**
Edit `backup_scripts/backup_daily.bat` with your settings

### 8.2 Schedule Backup

**Linux - Crontab:**
```bash
crontab -e
# Add: 0 2 * * * /home/user/AIT_CMMS2.3.1/backup_scripts/backup_daily.sh
```

**Windows - Task Scheduler:**
1. Task Scheduler → Create Basic Task
2. Daily at 2:00 AM
3. Action: Start program → Point to backup_daily.bat

### 8.3 Test Backup
```bash
# Linux
./backup_daily.sh

# Windows
backup_daily.bat
```

---

## PHASE 9: EMPLOYEE DEPLOYMENT (30 minutes per employee)

For each employee computer:

1. **Install Python** (same version as server)
2. **Install packages:**
   ```bash
   pip install psycopg2-binary pillow reportlab
   ```
3. **Copy CMMS folder** to their computer
4. **Update DB_CONFIG** in their copy:
   ```python
   'host': '192.168.1.100'  # Your laptop IP
   ```
5. **Test connection:**
   ```bash
   python AIT_CMMS_REV3.py
   ```

---

## CRITICAL REMINDERS

### Must Do:
- ✅ Keep laptop **powered on** during work hours
- ✅ Keep laptop **connected to network**
- ✅ **Daily backups** running automatically
- ✅ Monitor **disk space** regularly
- ✅ PostgreSQL **service always running**

### Network Setup:
- Use **static IP** for laptop (recommended)
- Add firewall rule for port 5432
- Configure router if remote access needed

### Security:
- Use **strong passwords**
- Restrict `pg_hba.conf` to your network only
- Keep backups in **multiple locations**

---

## TROUBLESHOOTING

### Can't connect to PostgreSQL
```bash
# Check service status
# Windows: Services → postgresql-x64-18
# Linux: sudo systemctl status postgresql

# Test connection
psql -U cmms_user -h localhost -d ait_cmms
```

### Employees can't connect
```bash
# Ping laptop from employee computer
ping 192.168.1.100

# Check firewall
# Temporarily disable to test

# Verify pg_hba.conf has correct network range
```

### Restore failed
```bash
# Option 1: Let app create tables, then restore data only
pg_restore --data-only ...

# Option 2: Drop and recreate database
dropdb -U postgres ait_cmms
createdb -U postgres ait_cmms
pg_restore ...
```

---

## MIGRATION TIMELINE

| Phase | Duration | Can Schedule After Hours? |
|-------|----------|---------------------------|
| 1. Setup PostgreSQL | 30 min | Yes |
| 2. Backup NEON | 15 min | Yes |
| 3. Configure Network | 20 min | Yes |
| 4. Create Database | 10 min | Yes |
| 5. Update Application | 5 min | Yes |
| 6. Restore Data | 15 min | Yes |
| 7. Testing | 20 min | Yes |
| 8. Setup Backups | 15 min | Yes |
| **Total** | **~2 hours** | **Recommended** |
| 9. Deploy to Employees | 30 min each | During work hours |

---

## MIGRATION DAY CHECKLIST

**Before Migration:**
- [ ] Inform employees of migration time
- [ ] Test PostgreSQL installation
- [ ] Create backup directory
- [ ] Note current NEON record counts

**During Migration:**
- [ ] Backup NEON database
- [ ] Configure PostgreSQL (network, firewall)
- [ ] Create database and user
- [ ] Update application config files (2 files)
- [ ] Restore data
- [ ] Test locally
- [ ] Test from another computer

**After Migration:**
- [ ] Verify all data present
- [ ] Test all critical functions
- [ ] Setup automated backups
- [ ] Deploy to employee computers
- [ ] Monitor for issues first week
- [ ] Keep NEON active for 1-2 weeks (fallback)
- [ ] Cancel NEON subscription

---

## FINAL NOTES

**Cost Savings:** $0 NEON fees going forward!

**Trade-offs:**
- ✅ No monthly fees
- ✅ Full control over data
- ✅ Faster (local network)
- ⚠️ You manage backups
- ⚠️ Laptop must stay on
- ⚠️ You handle maintenance

**Success Criteria:**
- All employees can connect
- All data present and correct
- Daily backups running
- No connection issues for 1 week

---

## SUPPORT

For detailed instructions on any step, see:
`MIGRATION_GUIDE_NEON_TO_LOCAL_POSTGRESQL.md`

**PostgreSQL Logs:**
- Windows: `C:\Program Files\PostgreSQL\18\data\log\`
- Linux: `/var/log/postgresql/`

**Quick Commands:**
```bash
# Connect to database
psql -U cmms_user -h localhost -d ait_cmms

# Check connections
SELECT * FROM pg_stat_activity WHERE datname='ait_cmms';

# Database size
SELECT pg_size_pretty(pg_database_size('ait_cmms'));

# Restart PostgreSQL
# Windows: net stop postgresql-x64-18 && net start postgresql-x64-18
# Linux: sudo systemctl restart postgresql
```

---

**Good luck with your migration!** 🚀
