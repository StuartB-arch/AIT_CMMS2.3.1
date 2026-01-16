@echo off
REM ############################################################################
REM AIT CMMS Restore Backup Script (Windows)
REM
REM This script restores a PostgreSQL database from a backup file
REM
REM Usage:
REM   restore_backup.bat backup_file.dump
REM
REM Example:
REM   restore_backup.bat C:\CMMS_Backups\ait_cmms_backup_20260116_140530.dump
REM ############################################################################

REM ==========================================================================
REM CONFIGURATION - EDIT THESE VALUES
REM ==========================================================================
set PGPASSWORD=your_postgres_password
set PG_BIN=C:\Program Files\PostgreSQL\18\bin
set DB_NAME=ait_cmms
set DB_USER=cmms_user
set DB_HOST=localhost
set DB_PORT=5432

REM ==========================================================================
REM SCRIPT START
REM ==========================================================================

REM Check if backup file is provided
if "%~1"=="" (
    echo ERROR: No backup file specified
    echo.
    echo Usage: %~nx0 ^<backup_file^>
    echo Example: %~nx0 C:\CMMS_Backups\ait_cmms_backup_20260116_140530.dump
    echo.
    echo Available backups:
    dir /b C:\CMMS_Backups\*.dump 2>nul
    if errorlevel 1 echo   No backups found
    exit /b 1
)

set BACKUP_FILE=%~1

REM Check if backup file exists
if not exist "%BACKUP_FILE%" (
    echo ERROR: Backup file not found: %BACKUP_FILE%
    exit /b 1
)

echo =========================================
echo AIT CMMS Database Restore
echo =========================================
echo Backup file: %BACKUP_FILE%
echo Database: %DB_NAME%
echo Host: %DB_HOST%:%DB_PORT%
echo User: %DB_USER%
echo.

REM Get file size
for %%A in ("%BACKUP_FILE%") do set BACKUP_SIZE=%%~zA
echo Backup size: %BACKUP_SIZE% bytes
echo.

REM Confirm restore
set /p confirm="WARNING: This will OVERWRITE the existing database. Continue? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo Restore cancelled.
    exit /b 0
)

echo.
echo Starting restore process...
echo.

REM Restore database
echo Restoring database from backup...
"%PG_BIN%\pg_restore" -U %DB_USER% -h %DB_HOST% -p %DB_PORT% -d %DB_NAME% --verbose --clean --if-exists "%BACKUP_FILE%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =========================================
    echo Restore completed successfully!
    echo =========================================

    REM Verify data
    echo.
    echo Verifying restored data...
    "%PG_BIN%\psql" -U %DB_USER% -h %DB_HOST% -p %DB_PORT% -d %DB_NAME% -c "SELECT 'equipment' as table_name, COUNT(*) as record_count FROM equipment UNION ALL SELECT 'users', COUNT(*) FROM users UNION ALL SELECT 'pm_completions', COUNT(*) FROM pm_completions UNION ALL SELECT 'corrective_maintenance', COUNT(*) FROM corrective_maintenance UNION ALL SELECT 'work_orders', COUNT(*) FROM work_orders;"

    echo.
    echo Restore process completed: %date% %time%
) else (
    echo.
    echo =========================================
    echo ERROR: Restore failed!
    echo =========================================
    echo Check the error messages above for details
    exit /b 1
)

REM Clear password variable
set PGPASSWORD=

exit /b 0
