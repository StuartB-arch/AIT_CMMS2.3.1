# Complete Beginner's Guide: Switching from Neon to PostgreSQL

## What This Guide Does

This guide will help you switch your CMMS (maintenance management system) from using Neon (a cloud database service) to using PostgreSQL on your own computer. This means:

- **No more monthly fees** to Neon (~$19-69/month)
- **Faster performance** (no internet needed)
- **Complete control** over your data
- **Works offline** - no internet required

**Time needed:** About 2-3 hours (most is waiting for downloads)

**Difficulty:** Easy - just follow the steps exactly!

---

## Before You Start - IMPORTANT!

### What You Need:
1. A Windows, Mac, or Linux computer
2. Administrator access (ability to install programs)
3. About 500 MB of free hard drive space
4. A cup of coffee ☕ (optional but recommended!)

### Safety First:
- We will backup your data before making ANY changes
- If something goes wrong, you can always go back to Neon
- Your current Neon database will stay active until you're sure everything works

---

## Part 1: Download and Install PostgreSQL

### Step 1.1: Download PostgreSQL

**For Windows:**
1. Open your web browser
2. Go to: https://www.postgresql.org/download/windows/
3. Click on "Download the installer"
4. Click on "Windows x86-64" for the latest version (18.1 or newer)
5. The file will download (about 350 MB) - wait for it to finish

**For Mac:**
1. Open your web browser
2. Go to: https://www.postgresql.org/download/macosx/
3. Download "Postgres.app" (easiest option for beginners)
   OR download the installer from EDB

**For Linux (Ubuntu/Debian):**
You'll install it from the command line in the next step.

---

### Step 1.2: Install PostgreSQL

**For Windows:**

1. **Find the downloaded file** (probably in your Downloads folder)
   - Look for something like `postgresql-18.1-windows-x64.exe`

2. **Double-click the file** to start installation

3. **Click "Next"** on the welcome screen

4. **Installation Directory:**
   - Just click "Next" (default location is fine)

5. **Select Components:**
   - Make sure these are checked:
     - ✅ PostgreSQL Server
     - ✅ pgAdmin 4 (this is a helpful tool)
     - ✅ Command Line Tools
   - Click "Next"

6. **Data Directory:**
   - Just click "Next" (default is fine)

7. **Set Password:**
   - **VERY IMPORTANT**: You need to create a password for the "postgres" user
   - Choose a strong password and **WRITE IT DOWN**
   - Example: `MySecureDB2024!`
   - You'll need this password later!
   - Click "Next"

8. **Port Number:**
   - Keep it as `5432`
   - Click "Next"

9. **Locale:**
   - Keep default
   - Click "Next"

10. **Summary:**
    - Click "Next" to start installation

11. **Wait for installation** (5-10 minutes)

12. **Finish:**
    - Uncheck "Launch Stack Builder"
    - Click "Finish"

**For Mac (using Postgres.app):**

1. Open the downloaded DMG file
2. Drag Postgres.app to your Applications folder
3. Open Postgres.app from Applications
4. Click "Initialize" when it asks
5. Done! PostgreSQL is running

**For Linux (Ubuntu/Debian):**

Open Terminal and run these commands one at a time:

```bash
# Update package list
sudo apt update

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

---

### Step 1.3: Verify PostgreSQL is Running

**For Windows:**

1. Press `Windows Key + R`
2. Type `services.msc` and press Enter
3. Look for "postgresql-x64-18" in the list
4. It should say "Running" in the Status column
5. If not, right-click it and select "Start"

**For Mac:**

1. Open Postgres.app
2. You should see a green indicator showing it's running

**For Linux:**

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql
```

You should see "active (running)" in green.

---

## Part 2: Backup Your Current Neon Database

This is the most important step - we need to save all your current data!

### Step 2.1: Install Database Backup Tool

**For Windows:**

The `pg_dump` tool was already installed with PostgreSQL. Let's make sure it works:

1. Press `Windows Key + R`
2. Type `cmd` and press Enter
3. Type this command and press Enter:
   ```
   "C:\Program Files\PostgreSQL\18\bin\pg_dump" --version
   ```
4. You should see something like "pg_dump (PostgreSQL) 18.1"

**For Mac/Linux:**

Open Terminal and type:
```bash
pg_dump --version
```

---

### Step 2.2: Create a Backup from Neon

Now we'll download all your data from Neon to your computer.

**For Windows:**

1. Open Command Prompt (Windows Key + R, type `cmd`, press Enter)

2. Navigate to a folder where you want to save the backup:
   ```
   cd C:\Users\YourName\Documents
   ```
   (Replace `YourName` with your actual username)

3. Create a backup folder:
   ```
   mkdir CMMS_Backup
   cd CMMS_Backup
   ```

4. Run this command (copy it exactly, it's one long line):
   ```
   "C:\Program Files\PostgreSQL\18\bin\pg_dump" -h ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech -p 5432 -U neondb_owner -d neondb -F c -f neon_backup.dump
   ```

5. When prompted for password, type: `npg_2Nm6hyPVWiIH` and press Enter

6. **Wait** - this might take 1-5 minutes depending on how much data you have

7. When finished, you should see a file called `neon_backup.dump` in your CMMS_Backup folder

**For Mac/Linux:**

1. Open Terminal

2. Navigate to your home directory and create a backup folder:
   ```bash
   cd ~
   mkdir CMMS_Backup
   cd CMMS_Backup
   ```

3. Run this command:
   ```bash
   pg_dump -h ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech -p 5432 -U neondb_owner -d neondb -F c -f neon_backup.dump
   ```

4. When prompted for password, type: `npg_2Nm6hyPVWiIH` and press Enter

5. Wait for it to complete

✅ **Success Check**: You should now have a file called `neon_backup.dump` saved on your computer!

---

## Part 3: Set Up Your Local PostgreSQL Database

Now we'll create a new database on your computer and set up a user account.

### Step 3.1: Connect to PostgreSQL

**For Windows:**

1. Press `Windows Key` and search for "SQL Shell (psql)"
2. Click on it to open
3. Press Enter 4 times (to accept defaults for Server, Database, Port, and Username)
4. When it asks for password, type the password you created during installation
5. You should see: `postgres=#`

**For Mac (Postgres.app):**

1. Open Postgres.app
2. Click "Open psql" (or double-click any database)
3. You should see a terminal window

**For Linux:**

```bash
sudo -u postgres psql
```

---

### Step 3.2: Create the Database and User

Now type these commands **one at a time**. Press Enter after each line.

```sql
-- Create a new database called 'ait_cmms'
CREATE DATABASE ait_cmms;
```

You should see: `CREATE DATABASE`

```sql
-- Create a user with a password
CREATE USER cmms_user WITH PASSWORD 'CMMS_2024_Secure!';
```

You should see: `CREATE ROLE`

**IMPORTANT**: Write down this password: `CMMS_2024_Secure!` (or change it to something else you'll remember)

```sql
-- Give the user permission to use the database
GRANT ALL PRIVILEGES ON DATABASE ait_cmms TO cmms_user;
```

You should see: `GRANT`

```sql
-- Connect to the new database
\c ait_cmms
```

You should see: `You are now connected to database "ait_cmms"`

```sql
-- Give the user permission to create tables
GRANT ALL ON SCHEMA public TO cmms_user;
```

You should see: `GRANT`

```sql
-- Exit PostgreSQL
\q
```

---

### Step 3.3: Restore Your Backup to the New Database

Now we'll copy all your data from the Neon backup into your new local database.

**For Windows:**

1. Open Command Prompt
2. Navigate to your backup folder:
   ```
   cd C:\Users\YourName\Documents\CMMS_Backup
   ```

3. Run this command to restore the backup:
   ```
   "C:\Program Files\PostgreSQL\18\bin\pg_restore" -h localhost -p 5432 -U cmms_user -d ait_cmms -v neon_backup.dump
   ```

4. When prompted for password, type: `CMMS_2024_Secure!` (or whatever password you set)

5. You'll see lots of text scrolling by - this is normal!

6. Wait for it to complete (might take 1-5 minutes)

**For Mac/Linux:**

```bash
cd ~/CMMS_Backup
pg_restore -h localhost -p 5432 -U cmms_user -d ait_cmms -v neon_backup.dump
```

Enter the password: `CMMS_2024_Secure!`

✅ **Success Check**: The command should complete without errors. If you see some warnings, that's usually okay!

---

## Part 4: Update Your CMMS Application

Now we need to tell your CMMS application to use the new local database instead of Neon.

### Step 4.1: Locate Your CMMS Folder

Your CMMS application is in this folder:
```
/home/user/AIT_CMMS2.3.1
```

**For Windows users:** This might be at:
- `C:\Users\YourName\AIT_CMMS2.3.1`

**For Mac users:** This might be at:
- `/Users/YourName/AIT_CMMS2.3.1`

---

### Step 4.2: EASY METHOD - Use the Automatic Configuration Tool

Your CMMS has a built-in tool to make this change automatically!

**For Windows:**

1. Open Command Prompt
2. Navigate to your CMMS folder:
   ```
   cd C:\Users\YourName\AIT_CMMS2.3.1
   ```

3. Run the configuration tool:
   ```
   python update_db_config.py
   ```

4. **Follow the prompts:**

   ```
   Do you want to use:
   1. LOCALHOST (single computer)
   2. NETWORK (multiple computers)
   3. Custom IP

   Enter your choice (1/2/3):
   ```

   - Type `1` if only YOU will use this on YOUR computer
   - Type `2` if OTHER people on your network will use it too
   - Press Enter

5. **Enter the password:**
   ```
   Enter database password:
   ```
   Type: `CMMS_2024_Secure!` and press Enter

6. **Done!** The tool will:
   - Create backups of your old configuration
   - Update both required files
   - Show you what it changed

**For Mac/Linux:**

```bash
cd /home/user/AIT_CMMS2.3.1
python3 update_db_config.py
```

Then follow the same prompts as above.

---

### Step 4.3: MANUAL METHOD (If you prefer to do it yourself)

If you want to see exactly what's changing, here's how to do it manually:

#### File 1: Update AIT_CMMS_REV3.py

1. **Open the file** in a text editor:
   - Windows: Right-click `AIT_CMMS_REV3.py` → "Edit with Notepad"
   - Mac/Linux: Use TextEdit or nano

2. **Find line 6906** (press Ctrl+G in most editors)

   You'll see this:
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

3. **Change it to this:**
   ```python
   self.DB_CONFIG = {
       'host': 'localhost',
       'port': 5432,
       'database': 'ait_cmms',
       'user': 'cmms_user',
       'password': 'CMMS_2024_Secure!',
       'sslmode': 'prefer'
   }
   ```

4. **Save the file** (Ctrl+S or File → Save)

#### File 2: Update migrate_multiuser.py

1. **Open the file** `migrate_multiuser.py`

2. **Find line 256**

   You'll see the same configuration

3. **Change it to match what you did in File 1:**
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

4. **Save the file**

---

## Part 5: Test Your CMMS Application

Time to see if everything works!

### Step 5.1: Start the Application

**For Windows:**

1. Open Command Prompt
2. Navigate to your CMMS folder:
   ```
   cd C:\Users\YourName\AIT_CMMS2.3.1
   ```

3. Run the application:
   ```
   python AIT_CMMS_REV3.py
   ```

**For Mac/Linux:**

```bash
cd /home/user/AIT_CMMS2.3.1
python3 AIT_CMMS_REV3.py
```

---

### Step 5.2: What to Check

When the application starts, check these things:

1. **Login Screen Appears**
   - ✅ You should see the login window
   - ✅ No error messages about database connection

2. **Can Login**
   - ✅ Try logging in with your username and password
   - ✅ You should see the main CMMS screen

3. **Data is There**
   - ✅ Check your equipment list - all items should be there
   - ✅ Check your maintenance records - they should all be there
   - ✅ Everything should look exactly like it did before!

4. **Can Add/Edit Data**
   - ✅ Try adding a new piece of equipment
   - ✅ Try editing an existing record
   - ✅ Try viewing a report

If ALL of these work - **CONGRATULATIONS!** 🎉 You successfully migrated!

---

## Part 6: What If Something Goes Wrong?

Don't panic! Here are solutions to common problems:

### Problem 1: "Connection refused" or "Could not connect to database"

**Solution:**

1. Make sure PostgreSQL is running:
   - **Windows**: Check services.msc for "postgresql-x64-18"
   - **Mac**: Open Postgres.app
   - **Linux**: `sudo systemctl status postgresql`

2. Check if you can connect manually:
   ```
   psql -h localhost -U cmms_user -d ait_cmms
   ```
   If this works, the problem is in your configuration files.

### Problem 2: "Password authentication failed"

**Solution:**

1. You probably typed the password wrong in the configuration
2. Double-check the password in both files:
   - AIT_CMMS_REV3.py (line 6906)
   - migrate_multiuser.py (line 256)
3. Make sure it matches the password you set in Step 3.2

### Problem 3: "Database does not exist"

**Solution:**

1. You need to create the database again:
   ```
   psql -U postgres
   CREATE DATABASE ait_cmms;
   \q
   ```

### Problem 4: "No data showing up"

**Solution:**

1. The database is there but empty
2. Re-run the restore command from Step 3.3
3. Make sure you're connected to the right database

### Problem 5: "Can't find pg_dump or pg_restore"

**Solution:**

**Windows**: Add PostgreSQL to your PATH:
1. Right-click "This PC" → Properties
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "System variables", find "Path"
5. Click "Edit"
6. Click "New"
7. Add: `C:\Program Files\PostgreSQL\18\bin`
8. Click OK on everything
9. Close and reopen Command Prompt

---

## Part 7: Going Back to Neon (If Needed)

If you need to go back to using Neon (temporarily or permanently):

### Option 1: Use the Automatic Tool

```bash
# If you kept the backup files
# The tool created backups with .backup extension
# Just rename them back

cd /home/user/AIT_CMMS2.3.1

# Windows:
move AIT_CMMS_REV3.py.backup AIT_CMMS_REV3.py
move migrate_multiuser.py.backup migrate_multiuser.py

# Mac/Linux:
mv AIT_CMMS_REV3.py.backup AIT_CMMS_REV3.py
mv migrate_multiuser.py.backup migrate_multiuser.py
```

### Option 2: Manually Change Back

Just change the DB_CONFIG back to the original Neon settings in both files:

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

---

## Part 8: Using CMMS with Multiple Computers (Optional)

If you want other people on your network to use the CMMS:

### Step 8.1: Find Your Computer's IP Address

**Windows:**
```
ipconfig
```
Look for "IPv4 Address" - it will be something like `192.168.1.100`

**Mac:**
```
ifconfig | grep "inet "
```

**Linux:**
```
ip addr show
```

### Step 8.2: Configure PostgreSQL to Accept Network Connections

**For Windows:**

1. Open File Explorer
2. Go to: `C:\Program Files\PostgreSQL\18\data`
3. Find the file `postgresql.conf`
4. Right-click → "Edit with Notepad"
5. Find the line `#listen_addresses = 'localhost'`
6. Change it to: `listen_addresses = '*'`
7. Save the file

8. Now edit `pg_hba.conf` in the same folder
9. Add this line at the bottom:
   ```
   host    ait_cmms    cmms_user    192.168.1.0/24    md5
   ```
   (This allows connections from your local network)

10. Restart PostgreSQL:
    - Press Windows Key + R
    - Type `services.msc`
    - Find "postgresql-x64-18"
    - Right-click → Restart

**For Mac/Linux:**

Similar steps - edit the files in your PostgreSQL data directory.

### Step 8.3: Update Configuration to Use Network IP

Instead of `localhost`, use your computer's IP address:

```python
self.DB_CONFIG = {
    'host': '192.168.1.100',  # Your computer's IP
    'port': 5432,
    'database': 'ait_cmms',
    'user': 'cmms_user',
    'password': 'CMMS_2024_Secure!',
    'sslmode': 'prefer'
}
```

Now other computers can access the database by using your IP address!

---

## Part 9: Setting Up Automatic Backups (Recommended!)

Since you're now responsible for your own backups, let's set up automatic daily backups.

### Step 9.1: Set Up Backup Script

Your CMMS already includes backup scripts!

**For Windows:**

1. Navigate to the backup scripts folder:
   ```
   cd C:\Users\YourName\AIT_CMMS2.3.1\backup_scripts
   ```

2. Open `backup_daily.bat` in Notepad

3. Update these lines with your password:
   ```
   set DB_PASSWORD=CMMS_2024_Secure!
   ```

4. Save the file

5. **Schedule it to run daily:**
   - Press Windows Key
   - Search for "Task Scheduler"
   - Click "Create Basic Task"
   - Name: "CMMS Daily Backup"
   - Trigger: Daily at 2:00 AM
   - Action: Start a program
   - Program: `C:\Users\YourName\AIT_CMMS2.3.1\backup_scripts\backup_daily.bat`
   - Finish

**For Mac/Linux:**

1. Edit the backup script:
   ```bash
   cd /home/user/AIT_CMMS2.3.1/backup_scripts
   nano backup_daily.sh
   ```

2. Update the password in the script

3. Make it executable:
   ```bash
   chmod +x backup_daily.sh
   ```

4. Add to crontab (schedule it):
   ```bash
   crontab -e
   ```

5. Add this line (runs at 2 AM daily):
   ```
   0 2 * * * /home/user/AIT_CMMS2.3.1/backup_scripts/backup_daily.sh
   ```

Now your database will be backed up automatically every night!

---

## Part 10: Cleanup and Final Steps

### Step 10.1: Keep Neon Active for 1 Week

Don't cancel your Neon subscription immediately! Keep it running for a week to make sure everything works with your new PostgreSQL setup.

After a week of successful operation, you can:
1. Log in to Neon
2. Downgrade to free tier or cancel subscription
3. Save money! 💰

### Step 10.2: Update Your Password (Security)

For better security, change your database password:

```sql
# Connect to PostgreSQL
psql -U postgres

# Change the password
ALTER USER cmms_user WITH PASSWORD 'YourNewStrongPassword123!';

\q
```

Then update both configuration files with the new password.

### Step 10.3: Test Backups Work

Test that you can restore from a backup:

1. Create a test database:
   ```sql
   psql -U postgres
   CREATE DATABASE test_restore;
   \q
   ```

2. Restore a recent backup to it:
   ```
   pg_restore -U cmms_user -d test_restore /path/to/backup/file.dump
   ```

3. If it works, delete the test database:
   ```sql
   psql -U postgres
   DROP DATABASE test_restore;
   \q
   ```

---

## Summary: What You Accomplished! 🎉

Congratulations! You just:

1. ✅ Installed PostgreSQL database software
2. ✅ Backed up all your data from Neon
3. ✅ Created a new local database
4. ✅ Restored all your data locally
5. ✅ Updated your CMMS configuration
6. ✅ Tested everything works
7. ✅ Set up automatic backups
8. ✅ Saved $228-828 per year!

Your CMMS now runs completely on your own computer with no internet required and no monthly fees!

---

## Quick Reference Commands

### Start PostgreSQL
**Windows**: services.msc → Find postgresql-x64-18 → Start
**Mac**: Open Postgres.app
**Linux**: `sudo systemctl start postgresql`

### Connect to Database
```bash
psql -U cmms_user -d ait_cmms
```

### Manual Backup
```bash
pg_dump -U cmms_user -d ait_cmms -F c -f backup_$(date +%Y%m%d).dump
```

### Manual Restore
```bash
pg_restore -U cmms_user -d ait_cmms backup_file.dump
```

### Start CMMS Application
```bash
cd /home/user/AIT_CMMS2.3.1
python3 AIT_CMMS_REV3.py
```

---

## Getting Help

### If You Get Stuck:

1. **Check the error message** - it usually tells you what's wrong
2. **Google the exact error** - others have probably had the same issue
3. **Check PostgreSQL is running** - this fixes 80% of problems
4. **Check your password** - this fixes another 15% of problems

### Resources:

- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Your existing migration guides in the AIT_CMMS2.3.1 folder:
  - `MIGRATION_GUIDE_NEON_TO_LOCAL_POSTGRESQL.md`
  - `QUICK_START_MIGRATION.md`

---

## Important Notes

1. **Keep your computer running** - If you turn off your computer, the database stops too
2. **Backups are YOUR responsibility** - Set up automatic backups (Part 9)
3. **Power settings** - Set your computer to not sleep if others need access
4. **Firewall** - If using multiple computers, you may need to allow port 5432

---

**You did it!** 🎊

Now go enjoy your free, fast, local database!
