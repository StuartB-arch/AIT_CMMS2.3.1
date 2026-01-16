# MIGRATION GUIDE: NEON to Local PostgreSQL Server
## AIT CMMS System - Database Migration

**Date:** 2026-01-16
**PostgreSQL Version:** 18.1
**Target Port:** 5432
**Goal:** Multi-user CMMS with local PostgreSQL server on laptop

---

## TABLE OF CONTENTS
1. [Current System Analysis](#1-current-system-analysis)
2. [PostgreSQL 18.1 Initial Setup](#2-postgresql-181-initial-setup)
3. [Backup NEON Database](#3-backup-neon-database)
4. [Configure PostgreSQL for Multi-User Access](#4-configure-postgresql-for-multi-user-access)
5. [Update Application Configuration](#5-update-application-configuration)
6. [Restore Data to Local PostgreSQL](#6-restore-data-to-local-postgresql)
7. [Test Migration](#7-test-migration)
8. [Network Setup for Employee Access](#8-network-setup-for-employee-access)
9. [Backup Strategy](#9-backup-strategy)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. CURRENT SYSTEM ANALYSIS

### Database Connection Configuration
Your CMMS currently connects to NEON with these settings:
- **Host:** ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech
- **Port:** 5432
- **Database:** neondb
- **User:** neondb_owner
- **Password:** npg_2Nm6hyPVWiIH
- **SSL Mode:** require

### Files to Update (2 files)
1. `/home/user/AIT_CMMS2.3.1/AIT_CMMS_REV3.py` (line 6820-6827)
2. `/home/user/AIT_CMMS2.3.1/migrate_multiuser.py` (line 256-263)

### Database Schema (19 tables)
Your system has:
- **Core tables:** equipment, pm_completions, weekly_pm_schedules, corrective_maintenance
- **Multi-user:** users, user_sessions, audit_log
- **Inventory:** parts_inventory, mro_stock, cm_parts_requests
- **Asset management:** cannot_find_assets, run_to_failure_assets, deactivated_assets, equipment_missing_parts
- **Work orders:** work_orders
- **KPI tracking:** kpi_definitions, kpi_manual_data, kpi_results, kpi_exports

---

## 2. POSTGRESQL 18.1 INITIAL SETUP

Since PostgreSQL 18.1 didn't prompt for password/port during installation, we need to configure it manually.

### Step 2.1: Locate PostgreSQL Installation

**On Windows:**
```cmd
cd "C:\Program Files\PostgreSQL\18"
```

**On Linux:**
```bash
cd /usr/lib/postgresql/18
```

**On macOS:**
```bash
cd /Library/PostgreSQL/18
```

### Step 2.2: Find Configuration Files

PostgreSQL configuration files are typically in:
- **Windows:** `C:\Program Files\PostgreSQL\18\data\`
- **Linux:** `/etc/postgresql/18/main/` or `/var/lib/postgresql/18/main/`
- **macOS:** `/Library/PostgreSQL/18/data/`

Look for these two critical files:
- `postgresql.conf` - Main configuration
- `pg_hba.conf` - Client authentication

### Step 2.3: Set PostgreSQL Password

**Option A: Using psql command-line (Recommended)**

1. Open Command Prompt/Terminal as Administrator
2. Navigate to PostgreSQL bin directory:
   ```cmd
   cd "C:\Program Files\PostgreSQL\18\bin"
   ```
3. Connect to PostgreSQL (it may not require password initially):
   ```cmd
   psql -U postgres
   ```
4. Set password for postgres user:
   ```sql
   ALTER USER postgres WITH PASSWORD 'your_secure_password';
   ```
   **Recommended password:** Use something secure like `AIT_CMMS_2024!` or generate a strong password
5. Exit psql:
   ```sql
   \q
   ```

**Option B: Using pgAdmin (if installed)**
1. Open pgAdmin
2. Connect to PostgreSQL Server (may not need password initially)
3. Right-click on "postgres" role → Properties
4. Go to "Definition" tab → Set password → Save

### Step 2.4: Verify Port 5432

Check if PostgreSQL is listening on port 5432:

**Windows:**
```cmd
netstat -ano | findstr :5432
```

**Linux/macOS:**
```bash
netstat -tuln | grep 5432
```

If port 5432 is not in use, PostgreSQL will use it by default. If something else is using it, we'll need to:

1. Open `postgresql.conf`
2. Find line: `port = 5432`
3. If commented out (has # at start), remove the #
4. Save file
5. Restart PostgreSQL service

**Restart PostgreSQL:**
- **Windows:** Services → PostgreSQL 18 → Restart
- **Linux:** `sudo systemctl restart postgresql`
- **macOS:** `brew services restart postgresql@18`

---

## 3. BACKUP NEON DATABASE

**CRITICAL:** Back up your data before migration!

### Step 3.1: Install PostgreSQL Client Tools (if not already installed)

Ensure you have `pg_dump` available. It comes with PostgreSQL 18.1 installation.

### Step 3.2: Create Backup Directory

```bash
mkdir -p /home/user/AIT_CMMS2.3.1/database_backups
cd /home/user/AIT_CMMS2.3.1/database_backups
```

### Step 3.3: Backup NEON Database

**Full database backup (recommended):**

```bash
pg_dump "postgresql://neondb_owner:npg_2Nm6hyPVWiIH@ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech:5432/neondb?sslmode=require" \
  --format=custom \
  --file=neon_backup_$(date +%Y%m%d_%H%M%S).dump
```

**Alternative: Plain SQL format (easier to inspect):**

```bash
pg_dump "postgresql://neondb_owner:npg_2Nm6hyPVWiIH@ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech:5432/neondb?sslmode=require" \
  --format=plain \
  --file=neon_backup_$(date +%Y%m%d_%H%M%S).sql
```

**Windows version:**
```cmd
pg_dump "postgresql://neondb_owner:npg_2Nm6hyPVWiIH@ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech:5432/neondb?sslmode=require" --format=custom --file=neon_backup.dump
```

### Step 3.4: Verify Backup

Check that the backup file was created and has reasonable size (should be > 0 KB):

**Linux/macOS:**
```bash
ls -lh neon_backup*.dump
```

**Windows:**
```cmd
dir neon_backup*.dump
```

**IMPORTANT:** Keep this backup safe! Copy it to multiple locations (external drive, cloud storage).

---

## 4. CONFIGURE POSTGRESQL FOR MULTI-USER ACCESS

For employees to connect from other computers, we need to configure PostgreSQL to accept network connections.

### Step 4.1: Get Your Laptop's IP Address

**Windows:**
```cmd
ipconfig
```
Look for "IPv4 Address" under your active network adapter (e.g., 192.168.1.100)

**Linux:**
```bash
ip addr show
```
or
```bash
hostname -I
```

**macOS:**
```bash
ifconfig
```

**Note your IP address. Example: 192.168.1.100**

### Step 4.2: Edit postgresql.conf

1. Open `postgresql.conf` in a text editor with admin rights:
   - **Windows:** `C:\Program Files\PostgreSQL\18\data\postgresql.conf`
   - **Linux:** `/etc/postgresql/18/main/postgresql.conf`

2. Find the line (usually around line 59):
   ```
   #listen_addresses = 'localhost'
   ```

3. Change it to listen on all network interfaces:
   ```
   listen_addresses = '*'
   ```
   Remove the `#` to uncomment it.

4. Verify port setting (should be around line 63):
   ```
   port = 5432
   ```

5. For better performance with multiple users, increase max connections (around line 66):
   ```
   max_connections = 20
   ```
   (Default is 100, but 20 is sufficient for small teams)

6. **Save the file**

### Step 4.3: Edit pg_hba.conf (Client Authentication)

This file controls who can connect to PostgreSQL.

1. Open `pg_hba.conf` in a text editor with admin rights:
   - **Windows:** `C:\Program Files\PostgreSQL\18\data\pg_hba.conf`
   - **Linux:** `/etc/postgresql/18/main/pg_hba.conf`

2. Scroll to the bottom of the file

3. Add entries to allow connections from your local network:

   ```
   # TYPE  DATABASE        USER            ADDRESS                 METHOD

   # Local connections
   host    all             all             127.0.0.1/32            scram-sha-256
   host    all             all             ::1/128                 scram-sha-256

   # Allow connections from local network (adjust to your network)
   # Example: If your network is 192.168.1.x
   host    all             all             192.168.1.0/24          scram-sha-256

   # Alternative: Allow from specific IP range (more secure)
   # host    all             all             192.168.1.100/32        scram-sha-256
   # host    all             all             192.168.1.101/32        scram-sha-256
   ```

   **Understanding the network mask:**
   - `192.168.1.0/24` - Allows all IPs from 192.168.1.1 to 192.168.1.254
   - `192.168.0.0/16` - Allows all IPs from 192.168.0.1 to 192.168.255.254
   - `10.0.0.0/8` - Allows all IPs from 10.0.0.1 to 10.255.255.255
   - Adjust based on your actual network configuration

4. **Save the file**

### Step 4.4: Configure Windows Firewall (Windows only)

Allow PostgreSQL through Windows Firewall:

**Option A: Using Command Prompt (as Administrator)**
```cmd
netsh advfirewall firewall add rule name="PostgreSQL" dir=in action=allow protocol=TCP localport=5432
```

**Option B: Using GUI**
1. Open Windows Defender Firewall → Advanced Settings
2. Click "Inbound Rules" → "New Rule"
3. Select "Port" → Next
4. Select TCP, enter port 5432 → Next
5. Select "Allow the connection" → Next
6. Check all profiles (Domain, Private, Public) → Next
7. Name: "PostgreSQL Server" → Finish

### Step 4.5: Restart PostgreSQL Service

**Windows:**
1. Open Services (services.msc)
2. Find "postgresql-x64-18" or "PostgreSQL 18"
3. Right-click → Restart

**Linux:**
```bash
sudo systemctl restart postgresql
```

**macOS:**
```bash
brew services restart postgresql@18
```

### Step 4.6: Verify PostgreSQL is Listening

**Check if PostgreSQL accepts connections:**

From your laptop (local):
```bash
psql -U postgres -h localhost -p 5432
```

From another computer on the network:
```bash
psql -U postgres -h 192.168.1.100 -p 5432
```
(Replace 192.168.1.100 with your laptop's IP)

If you can connect, configuration is successful!

---

## 5. UPDATE APPLICATION CONFIGURATION

### Step 5.1: Create New Database and User

1. Connect to PostgreSQL:
   ```bash
   psql -U postgres -h localhost
   ```

2. Create database for CMMS:
   ```sql
   CREATE DATABASE ait_cmms;
   ```

3. Create dedicated user for CMMS:
   ```sql
   CREATE USER cmms_user WITH PASSWORD 'your_secure_password';
   ```
   **Recommended password:** Something like `CMMS_2024_Secure!`

4. Grant all privileges:
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE ait_cmms TO cmms_user;
   \c ait_cmms
   GRANT ALL ON SCHEMA public TO cmms_user;
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cmms_user;
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cmms_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cmms_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cmms_user;
   ```

5. Exit psql:
   ```sql
   \q
   ```

### Step 5.2: Update AIT_CMMS_REV3.py Configuration

**File:** `/home/user/AIT_CMMS2.3.1/AIT_CMMS_REV3.py` (lines 6820-6827)

**OLD Configuration:**
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

**NEW Configuration:**
```python
self.DB_CONFIG = {
    'host': 'localhost',  # Or your laptop's IP: '192.168.1.100'
    'port': 5432,
    'database': 'ait_cmms',
    'user': 'cmms_user',
    'password': 'CMMS_2024_Secure!',  # Use the password you set
    'sslmode': 'prefer'  # Changed from 'require' to 'prefer'
}
```

**Notes:**
- Use `'localhost'` when running on the same computer as PostgreSQL
- Use your laptop's IP (e.g., `'192.168.1.100'`) when employees connect from other computers
- Change `sslmode` from `'require'` to `'prefer'` (local PostgreSQL doesn't require SSL by default)

### Step 5.3: Update migrate_multiuser.py Configuration

**File:** `/home/user/AIT_CMMS2.3.1/migrate_multiuser.py` (lines 256-263)

Make the **EXACT SAME** changes as Step 5.2:

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ait_cmms',
    'user': 'cmms_user',
    'password': 'CMMS_2024_Secure!',
    'sslmode': 'prefer'
}
```

### Step 5.4: Create Configuration File (Optional but Recommended)

For easier management, create a centralized config file:

**Create:** `/home/user/AIT_CMMS2.3.1/db_config.py`

```python
"""
Database Configuration for AIT CMMS
Centralized database settings
"""

# For local laptop server
DB_CONFIG = {
    'host': 'localhost',  # Change to laptop IP for network access
    'port': 5432,
    'database': 'ait_cmms',
    'user': 'cmms_user',
    'password': 'CMMS_2024_Secure!',
    'sslmode': 'prefer'
}

# Network configuration (when deploying to employees)
# Uncomment and update the IP address
"""
DB_CONFIG = {
    'host': '192.168.1.100',  # Your laptop's IP
    'port': 5432,
    'database': 'ait_cmms',
    'user': 'cmms_user',
    'password': 'CMMS_2024_Secure!',
    'sslmode': 'prefer'
}
"""
```

Then import it in your main files:
```python
from db_config import DB_CONFIG
```

---

## 6. RESTORE DATA TO LOCAL POSTGRESQL

### Step 6.1: Restore Database from Backup

**If you used custom format (.dump):**

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

**If you used plain SQL format (.sql):**

```bash
psql -U cmms_user -h localhost -d ait_cmms -f neon_backup_YYYYMMDD_HHMMSS.sql
```

You'll be prompted for the password (cmms_user password you set earlier).

### Step 6.2: Verify Data Import

Connect to the database and check tables:

```bash
psql -U cmms_user -h localhost -d ait_cmms
```

Run these queries:

```sql
-- List all tables
\dt

-- Count records in key tables
SELECT 'equipment' as table_name, COUNT(*) as record_count FROM equipment
UNION ALL
SELECT 'users', COUNT(*) FROM users
UNION ALL
SELECT 'pm_completions', COUNT(*) FROM pm_completions
UNION ALL
SELECT 'corrective_maintenance', COUNT(*) FROM corrective_maintenance
UNION ALL
SELECT 'work_orders', COUNT(*) FROM work_orders;

-- Check a sample record
SELECT * FROM equipment LIMIT 5;

-- Exit
\q
```

**Expected results:**
- You should see all 19 tables
- Record counts should match your NEON database
- Sample records should display correctly

### Step 6.3: Handle Schema Differences (if any)

If the restore fails due to schema issues, you can:

**Option A: Let the application create tables (recommended for fresh start)**
1. Skip the restore for now
2. Run the application - it will create all tables automatically
3. Then manually migrate critical data using export/import

**Option B: Manual table creation**
1. The application's `init_database()` function will create all tables
2. You can run it by starting the application once
3. Then restore only the data (not schema)

---

## 7. TEST MIGRATION

### Step 7.1: Test Local Connection

1. Open terminal/command prompt
2. Navigate to CMMS directory:
   ```bash
   cd /home/user/AIT_CMMS2.3.1
   ```

3. Run the application:
   ```bash
   python AIT_CMMS_REV3.py
   ```

4. **Expected behavior:**
   - Application should start without connection errors
   - Login screen should appear
   - You should be able to login with existing credentials
   - All modules should load correctly

5. **Test critical functions:**
   - [ ] Login with existing user
   - [ ] View equipment list
   - [ ] Create a test PM completion
   - [ ] Create a test CM work order
   - [ ] View reports
   - [ ] Check KPI dashboard
   - [ ] Log out

### Step 7.2: Test from Another Computer (Multi-User Test)

**On your laptop (server):**
1. Note your IP address (e.g., 192.168.1.100)
2. Update `DB_CONFIG` in both files to use your IP instead of 'localhost'

**On employee's computer:**
1. Install Python and required dependencies
2. Copy the CMMS application folder to employee's computer
3. Ensure `DB_CONFIG` points to your laptop's IP
4. Run the application:
   ```bash
   python AIT_CMMS_REV3.py
   ```

5. **Test concurrent access:**
   - Log in as different users from different computers simultaneously
   - Both users should be able to work without conflicts
   - Test editing the same record (optimistic locking should prevent conflicts)

### Step 7.3: Monitor PostgreSQL Connections

**Check active connections:**

```sql
SELECT pid, usename, application_name, client_addr, state, query_start
FROM pg_stat_activity
WHERE datname = 'ait_cmms';
```

You should see connections from different client IP addresses when employees connect.

---

## 8. NETWORK SETUP FOR EMPLOYEE ACCESS

### Step 8.1: Static IP Address (Recommended)

To ensure your laptop always has the same IP:

**Windows:**
1. Control Panel → Network and Sharing Center
2. Click your network connection → Properties
3. Select "Internet Protocol Version 4 (TCP/IPv4)" → Properties
4. Select "Use the following IP address"
5. Enter:
   - IP address: 192.168.1.100 (or your chosen IP)
   - Subnet mask: 255.255.255.0
   - Default gateway: 192.168.1.1 (your router's IP)
   - DNS: 8.8.8.8 (Google DNS)
6. Click OK → OK

**Linux:**
Edit `/etc/network/interfaces` or use NetworkManager GUI

**macOS:**
System Preferences → Network → Advanced → TCP/IP → Configure IPv4: Manually

### Step 8.2: Configure Router (if needed)

If employees connect from outside your immediate network:

1. Log into your router (usually http://192.168.1.1)
2. Set up **Port Forwarding**:
   - External Port: 5432
   - Internal IP: Your laptop's IP (192.168.1.100)
   - Internal Port: 5432
   - Protocol: TCP
3. Note your **public IP address** (google "what is my ip")
4. Update `DB_CONFIG` host to your public IP for remote employees

**SECURITY WARNING:** Opening PostgreSQL to the internet is risky!

**Better alternatives:**
- **VPN:** Set up VPN so remote employees connect to your network securely
- **SSH Tunnel:** Employees connect via SSH tunnel
- **Local network only:** Keep it simple if all employees are on-site

### Step 8.3: DNS/Hostname Setup (Advanced - Optional)

Instead of IP addresses, use a hostname:

1. Set up **Dynamic DNS** service (e.g., No-IP, DuckDNS)
2. Configure your router to update DDNS
3. Update `DB_CONFIG` host to: `'yourcompany.ddns.net'`

This way, even if your IP changes, the hostname stays the same.

### Step 8.4: Employee Workstation Setup

**On each employee computer:**

1. **Install Python** (same version as server)
2. **Install required packages:**
   ```bash
   pip install psycopg2-binary pillow reportlab tkinter
   ```
3. **Copy CMMS application folder** to their computer
4. **Update DB_CONFIG** in their local copy:
   ```python
   DB_CONFIG = {
       'host': '192.168.1.100',  # Your laptop's IP
       'port': 5432,
       'database': 'ait_cmms',
       'user': 'cmms_user',
       'password': 'CMMS_2024_Secure!',
       'sslmode': 'prefer'
   }
   ```
5. **Create desktop shortcut** for easy access

**Test connectivity from employee computer:**
```bash
psql -h 192.168.1.100 -U cmms_user -d ait_cmms -p 5432
```

---

## 9. BACKUP STRATEGY

**CRITICAL:** Without NEON's automatic backups, YOU are responsible for backups!

### Step 9.1: Automated Daily Backups

**Create backup script:**

**Windows - Create:** `C:\CMMS_Backups\backup_daily.bat`
```bat
@echo off
set PGPASSWORD=your_postgres_password
set BACKUP_DIR=C:\CMMS_Backups
set TIMESTAMP=%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

"C:\Program Files\PostgreSQL\18\bin\pg_dump" -U postgres -h localhost -d ait_cmms -F c -f "%BACKUP_DIR%\ait_cmms_backup_%TIMESTAMP%.dump"

:: Keep only last 30 days of backups
forfiles /p "%BACKUP_DIR%" /s /m *.dump /d -30 /c "cmd /c del @path"

echo Backup completed: %TIMESTAMP%
```

**Linux/macOS - Create:** `/home/user/backup_daily.sh`
```bash
#!/bin/bash
export PGPASSWORD='your_postgres_password'
BACKUP_DIR="/home/user/CMMS_Backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

pg_dump -U postgres -h localhost -d ait_cmms -F c -f "$BACKUP_DIR/ait_cmms_backup_$TIMESTAMP.dump"

# Keep only last 30 days
find "$BACKUP_DIR" -name "*.dump" -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
```

Make it executable:
```bash
chmod +x /home/user/backup_daily.sh
```

### Step 9.2: Schedule Automated Backups

**Windows - Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task → Name: "CMMS Daily Backup"
3. Trigger: Daily at 2:00 AM
4. Action: Start a program
5. Program: `C:\CMMS_Backups\backup_daily.bat`
6. Finish

**Linux - Crontab:**
```bash
crontab -e
```
Add line:
```
0 2 * * * /home/user/backup_daily.sh >> /home/user/backup.log 2>&1
```

**macOS - Launchd:**
Create `/Library/LaunchDaemons/com.ait.cmms.backup.plist`

### Step 9.3: Off-Site Backup Storage

**Critical:** Store backups in multiple locations!

**Options:**
1. **External Hard Drive** - Automatically copy backups to USB drive
2. **Network Storage (NAS)** - Save to network share
3. **Cloud Storage** - Sync backup folder to Dropbox/Google Drive/OneDrive
4. **Second Computer** - Rsync/robocopy to another machine

**Example - Windows cloud sync:**
Configure backup directory `C:\CMMS_Backups` to sync with OneDrive or Google Drive.

**Example - Linux rsync to NAS:**
```bash
rsync -avz /home/user/CMMS_Backups/ /mnt/nas/CMMS_Backups/
```

---

## 10. TROUBLESHOOTING

### Issue 1: Can't Connect to PostgreSQL

**Symptoms:** Application shows connection error

**Solutions:**
1. **Check PostgreSQL is running:**
   - Windows: Services → postgresql-x64-18 → Status should be "Running"
   - Linux: `sudo systemctl status postgresql`

2. **Verify port 5432:**
   ```bash
   netstat -ano | findstr :5432  # Windows
   netstat -tuln | grep 5432     # Linux
   ```

3. **Test connection manually:**
   ```bash
   psql -U cmms_user -h localhost -d ait_cmms -p 5432
   ```

4. **Check password:** Ensure DB_CONFIG password matches PostgreSQL user password

### Issue 2: Employees Can't Connect from Other Computers

**Symptoms:** Connection timeout or "could not connect to server"

**Solutions:**
1. **Verify laptop IP address:**
   ```cmd
   ipconfig  # Windows
   ip addr   # Linux
   ```

2. **Ping laptop from employee computer:**
   ```cmd
   ping 192.168.1.100
   ```
   Should get replies. If not, network issue.

3. **Check firewall:**
   - Windows: Ensure port 5432 rule is active in Windows Firewall
   - Test: Temporarily disable firewall to isolate issue

4. **Check pg_hba.conf:**
   - Ensure employee's IP range is allowed
   - Restart PostgreSQL after changes

5. **Check postgresql.conf:**
   - Ensure `listen_addresses = '*'`
   - Restart PostgreSQL after changes

6. **Test from employee computer:**
   ```bash
   psql -h 192.168.1.100 -U cmms_user -d ait_cmms -p 5432
   ```
   Should prompt for password.

### Issue 3: Data Not Imported Correctly

**Symptoms:** Tables are empty or missing data

**Solutions:**
1. **Re-run backup from NEON:**
   ```bash
   pg_dump "postgresql://neondb_owner:npg_2Nm6hyPVWiIH@ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech:5432/neondb?sslmode=require" -F c -f neon_backup_new.dump
   ```

2. **Drop and recreate database:**
   ```sql
   DROP DATABASE ait_cmms;
   CREATE DATABASE ait_cmms;
   GRANT ALL PRIVILEGES ON DATABASE ait_cmms TO cmms_user;
   ```

3. **Restore with verbose output:**
   ```bash
   pg_restore --host=localhost --port=5432 --username=cmms_user --dbname=ait_cmms --verbose neon_backup_new.dump
   ```
   Check for errors in output.

4. **Alternative: Let application create schema, then import data only:**
   - Run application once to create tables
   - Use `pg_dump --data-only` from NEON
   - Restore data with `pg_restore --data-only`

### Issue 4: Permission Denied Errors

**Symptoms:** "permission denied for table" or "must be owner of database"

**Solutions:**
1. **Grant all privileges to cmms_user:**
   ```sql
   \c ait_cmms
   GRANT ALL ON SCHEMA public TO cmms_user;
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cmms_user;
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cmms_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cmms_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cmms_user;
   ```

2. **Or restore as superuser (postgres):**
   ```bash
   pg_restore -U postgres -d ait_cmms neon_backup.dump
   ```

### Issue 5: Slow Performance with Multiple Users

**Symptoms:** Application is slow when multiple employees are using it

**Solutions:**
1. **Increase connection pool size** in `database_utils.py`:
   ```python
   db_pool.initialize(self.DB_CONFIG, min_conn=2, max_conn=20)
   ```

2. **Increase PostgreSQL shared buffers** in `postgresql.conf`:
   ```
   shared_buffers = 256MB  # Increase from default 128MB
   ```

3. **Add more indexes** for commonly queried fields

4. **Check disk space:** Ensure laptop has adequate free space

5. **Monitor queries:**
   ```sql
   SELECT * FROM pg_stat_activity WHERE state = 'active';
   ```

### Issue 6: Laptop Sleeps/Network Disconnects

**Symptoms:** Employees lose connection when laptop goes to sleep

**Solutions:**
1. **Disable laptop sleep:**
   - Windows: Power Options → Never sleep when plugged in
   - macOS: System Preferences → Energy Saver → Prevent sleep

2. **Keep laptop plugged in** and connected to network always

3. **Configure connection keepalive** (already done in database_utils.py):
   - The system has built-in keepalive pings every 20 seconds
   - This should prevent connection drops

4. **Consider dedicated server:** For production use, a dedicated always-on computer is better than a laptop

### Issue 7: Port 5432 Already in Use

**Symptoms:** PostgreSQL won't start, port conflict

**Solutions:**
1. **Find what's using port 5432:**
   ```cmd
   netstat -ano | findstr :5432  # Windows
   ```
   Note the PID (Process ID)

2. **Check if it's another PostgreSQL instance:**
   - Task Manager → Details → Find PID → End Task (if safe)

3. **Use different port:**
   - Edit `postgresql.conf`: `port = 5433`
   - Update `DB_CONFIG` in application: `'port': 5433`
   - Restart PostgreSQL

### Issue 8: "SSL Connection Required" Error

**Symptoms:** Error about SSL when connecting

**Solutions:**
1. **Change sslmode in DB_CONFIG:**
   ```python
   'sslmode': 'disable'  # Instead of 'prefer' or 'require'
   ```

2. **Or enable SSL in PostgreSQL:**
   - This is more complex and usually unnecessary for local networks
   - Stick with `sslmode: 'disable'` or `'prefer'` for simplicity

---

## MIGRATION CHECKLIST

Use this checklist to track your progress:

### Pre-Migration
- [ ] Understand current NEON configuration
- [ ] Note current database size and record counts
- [ ] Inform employees of migration schedule
- [ ] Plan for downtime/migration window

### PostgreSQL Setup
- [ ] PostgreSQL 18.1 installed
- [ ] Set postgres user password
- [ ] Verify port 5432 is available
- [ ] PostgreSQL service is running

### Backup
- [ ] Full NEON database backup created (.dump file)
- [ ] Backup file verified (file size > 0)
- [ ] Backup copied to safe location(s)
- [ ] Test backup file integrity

### Network Configuration
- [ ] Laptop IP address noted
- [ ] Static IP configured (if needed)
- [ ] postgresql.conf edited (listen_addresses = '*')
- [ ] pg_hba.conf edited (network access allowed)
- [ ] Windows Firewall rule created (port 5432)
- [ ] PostgreSQL service restarted
- [ ] Test connection from localhost
- [ ] Test connection from another computer

### Database Setup
- [ ] New database 'ait_cmms' created
- [ ] New user 'cmms_user' created
- [ ] Privileges granted to cmms_user
- [ ] Data restored from NEON backup
- [ ] Verify table count (19 tables)
- [ ] Verify record counts match NEON

### Application Configuration
- [ ] Update AIT_CMMS_REV3.py DB_CONFIG
- [ ] Update migrate_multiuser.py DB_CONFIG
- [ ] (Optional) Create centralized db_config.py
- [ ] Test application startup locally
- [ ] Test all critical functions

### Multi-User Testing
- [ ] Update DB_CONFIG with laptop IP
- [ ] Deploy application to employee computers
- [ ] Test login from multiple computers
- [ ] Test concurrent access
- [ ] Test optimistic locking (edit conflicts)
- [ ] Monitor connection pool

### Backup Strategy
- [ ] Automated backup script created
- [ ] Backup script tested manually
- [ ] Scheduled task/cron job configured
- [ ] Off-site backup location configured
- [ ] Test restore from backup

### Finalization
- [ ] Document laptop IP address for employees
- [ ] Create employee connection guide
- [ ] Monitor for issues first few days
- [ ] Verify all employees can connect
- [ ] Keep NEON database running for 1-2 weeks as fallback
- [ ] After successful migration, cancel NEON subscription

---

## SUMMARY

### What Changes in Your Application:

**Before (NEON):**
- Host: `ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech`
- SSL required
- Managed service (automatic backups, updates)
- Internet connection required

**After (Local PostgreSQL):**
- Host: `localhost` or `192.168.1.100` (your laptop)
- SSL optional (prefer or disable)
- You manage backups and maintenance
- Local network connection required
- No monthly fees!

### Files to Modify (2 files):
1. `/home/user/AIT_CMMS2.3.1/AIT_CMMS_REV3.py` (line 6820-6827)
2. `/home/user/AIT_CMMS2.3.1/migrate_multiuser.py` (line 256-263)

### Key Configuration Change:
```python
# Change these values in DB_CONFIG:
'host': 'localhost'  # or your laptop IP
'database': 'ait_cmms'  # new database name
'user': 'cmms_user'  # new user
'password': 'your_new_password'  # new password
'sslmode': 'prefer'  # changed from 'require'
```

### Critical Success Factors:
1. **Always keep laptop powered on** during work hours
2. **Laptop must stay connected to network**
3. **Run daily backups** - you are now responsible!
4. **Static IP recommended** for laptop
5. **Monitor disk space** - database will grow over time
6. **Keep PostgreSQL service running** at all times

### Cost Savings:
- NEON subscription: $0/month (eliminated!)
- Total migration cost: $0 (just your time)

---

## NEED HELP?

If you encounter issues:
1. Check the Troubleshooting section (#10)
2. Verify each step in the Migration Checklist
3. Test connection manually with psql
4. Check PostgreSQL logs for error messages
5. Ensure firewall/network configuration is correct

**PostgreSQL Log Locations:**
- Windows: `C:\Program Files\PostgreSQL\18\data\log\`
- Linux: `/var/log/postgresql/`
- macOS: `/usr/local/var/postgres/`

---

## APPENDIX: Quick Reference Commands

### PostgreSQL Service Management

**Windows:**
```cmd
# Start service
net start postgresql-x64-18

# Stop service
net stop postgresql-x64-18

# Restart service
net stop postgresql-x64-18 && net start postgresql-x64-18
```

**Linux:**
```bash
sudo systemctl start postgresql
sudo systemctl stop postgresql
sudo systemctl restart postgresql
sudo systemctl status postgresql
```

### Database Connection

```bash
# Connect locally
psql -U postgres -h localhost

# Connect to specific database
psql -U cmms_user -h localhost -d ait_cmms

# Connect from remote computer
psql -U cmms_user -h 192.168.1.100 -d ait_cmms -p 5432
```

### Backup & Restore

```bash
# Backup (custom format)
pg_dump -U postgres -h localhost -d ait_cmms -F c -f backup.dump

# Backup (SQL format)
pg_dump -U postgres -h localhost -d ait_cmms -f backup.sql

# Restore (custom format)
pg_restore -U cmms_user -h localhost -d ait_cmms backup.dump

# Restore (SQL format)
psql -U cmms_user -h localhost -d ait_cmms -f backup.sql
```

### Useful SQL Commands

```sql
-- List databases
\l

-- Connect to database
\c ait_cmms

-- List tables
\dt

-- Describe table
\d equipment

-- Show table size
SELECT pg_size_pretty(pg_total_relation_size('equipment'));

-- Show database size
SELECT pg_size_pretty(pg_database_size('ait_cmms'));

-- List active connections
SELECT * FROM pg_stat_activity WHERE datname = 'ait_cmms';

-- Kill a connection (if needed)
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = 12345;

-- Exit psql
\q
```

---

**END OF MIGRATION GUIDE**

Good luck with your migration! This will save you money and give you full control over your CMMS database.
