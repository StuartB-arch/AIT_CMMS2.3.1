@echo off
REM ############################################################################
REM AIT CMMS Daily Backup Script (Windows)
REM
REM This script creates daily backups of the PostgreSQL database
REM and removes backups older than 30 days
REM
REM Setup Instructions:
REM 1. Edit the configuration variables below
REM 2. Open Task Scheduler
REM 3. Create Basic Task -> Daily at 2:00 AM
REM 4. Action: Start a program -> Point to this .bat file
REM ############################################################################

REM ==========================================================================
REM CONFIGURATION - EDIT THESE VALUES
REM ==========================================================================
set PGPASSWORD=your_postgres_password
set PG_BIN=C:\Program Files\PostgreSQL\18\bin
set BACKUP_DIR=C:\CMMS_Backups
set DB_NAME=ait_cmms
set DB_USER=postgres
set DB_HOST=localhost
set DB_PORT=5432
set RETENTION_DAYS=30

REM ==========================================================================
REM SCRIPT START - DO NOT EDIT BELOW THIS LINE
REM ==========================================================================

REM Create backup directory if it doesn't exist
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Generate timestamp (format: YYYYMMDD_HHMMSS)
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "TIMESTAMP=%dt:~0,4%%dt:~4,2%%dt:~6,2%_%dt:~8,2%%dt:~10,2%%dt:~12,2%"
set "DATE_ONLY=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%"

REM Backup file names
set BACKUP_FILE=%BACKUP_DIR%\ait_cmms_backup_%TIMESTAMP%.dump
set LOG_FILE=%BACKUP_DIR%\backup_log_%DATE_ONLY%.txt

REM Start backup
echo ======================================== >> "%LOG_FILE%"
echo Backup started: %date% %time% >> "%LOG_FILE%"
echo Database: %DB_NAME% >> "%LOG_FILE%"
echo Host: %DB_HOST%:%DB_PORT% >> "%LOG_FILE%"

REM Create backup using pg_dump
"%PG_BIN%\pg_dump" -U %DB_USER% -h %DB_HOST% -p %DB_PORT% -d %DB_NAME% -F c -f "%BACKUP_FILE%" 2>> "%LOG_FILE%"

if %ERRORLEVEL% EQU 0 (
    echo Backup completed successfully! >> "%LOG_FILE%"
    echo File: %BACKUP_FILE% >> "%LOG_FILE%"

    REM Get file size
    for %%A in ("%BACKUP_FILE%") do set BACKUP_SIZE=%%~zA
    echo Size: %BACKUP_SIZE% bytes >> "%LOG_FILE%"

    REM Remove old backups
    echo Removing backups older than %RETENTION_DAYS% days... >> "%LOG_FILE%"
    forfiles /p "%BACKUP_DIR%" /s /m *.dump /d -%RETENTION_DAYS% /c "cmd /c del @path" 2>nul

    REM Count remaining backups
    dir /b "%BACKUP_DIR%\*.dump" 2>nul | find /c /v "" > temp.txt
    set /p BACKUP_COUNT=<temp.txt
    del temp.txt
    echo Total backups retained: %BACKUP_COUNT% >> "%LOG_FILE%"

    echo Backup process completed: %date% %time% >> "%LOG_FILE%"
    echo Status: SUCCESS >> "%LOG_FILE%"
) else (
    echo ERROR: Backup failed! >> "%LOG_FILE%"
    echo Status: FAILED >> "%LOG_FILE%"
    echo Check PostgreSQL logs for details >> "%LOG_FILE%"
)

echo ======================================== >> "%LOG_FILE%"

REM Clear password variable
set PGPASSWORD=

exit /b 0
