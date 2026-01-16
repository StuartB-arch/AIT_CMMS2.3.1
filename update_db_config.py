#!/usr/bin/env python3
"""
Database Configuration Updater for AIT CMMS
This script helps update database connection settings in both required files
"""

import os
import re
import socket
import sys

# Configuration templates
LOCALHOST_CONFIG = """    self.DB_CONFIG = {
        'host': 'localhost',
        'port': 5432,
        'database': 'ait_cmms',
        'user': 'cmms_user',
        'password': '{password}',
        'sslmode': 'prefer'
    }"""

NETWORK_CONFIG = """    self.DB_CONFIG = {
        'host': '{host}',
        'port': 5432,
        'database': 'ait_cmms',
        'user': 'cmms_user',
        'password': '{password}',
        'sslmode': 'prefer'
    }"""

MIGRATE_LOCALHOST_CONFIG = """DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ait_cmms',
    'user': 'cmms_user',
    'password': '{password}',
    'sslmode': 'prefer'
}"""

MIGRATE_NETWORK_CONFIG = """DB_CONFIG = {
    'host': '{host}',
    'port': 5432,
    'database': 'ait_cmms',
    'user': 'cmms_user',
    'password': '{password}',
    'sslmode': 'prefer'
}"""


def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "192.168.1.100"  # Default fallback


def read_file(file_path):
    """Read file contents"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"ERROR: File not found: {file_path}")
        return None


def write_file(file_path, content):
    """Write content to file"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"ERROR writing to {file_path}: {e}")
        return False


def update_main_config(content, host, password):
    """Update DB_CONFIG in AIT_CMMS_REV3.py"""
    # Pattern to match the DB_CONFIG dictionary
    pattern = r'self\.DB_CONFIG\s*=\s*\{[^}]+\}'

    if host.lower() == 'localhost':
        new_config = LOCALHOST_CONFIG.format(password=password)
    else:
        new_config = NETWORK_CONFIG.format(host=host, password=password)

    # Replace the configuration
    updated_content = re.sub(pattern, new_config, content, flags=re.DOTALL)

    if updated_content == content:
        print("WARNING: DB_CONFIG pattern not found in AIT_CMMS_REV3.py")
        return None

    return updated_content


def update_migrate_config(content, host, password):
    """Update DB_CONFIG in migrate_multiuser.py"""
    # Pattern to match the DB_CONFIG dictionary
    pattern = r'DB_CONFIG\s*=\s*\{[^}]+\}'

    if host.lower() == 'localhost':
        new_config = MIGRATE_LOCALHOST_CONFIG.format(password=password)
    else:
        new_config = MIGRATE_NETWORK_CONFIG.format(host=host, password=password)

    # Replace the configuration
    updated_content = re.sub(pattern, new_config, content, flags=re.DOTALL)

    if updated_content == content:
        print("WARNING: DB_CONFIG pattern not found in migrate_multiuser.py")
        return None

    return updated_content


def backup_file(file_path):
    """Create a backup of the file"""
    backup_path = file_path + ".backup"
    try:
        content = read_file(file_path)
        if content:
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Backup created: {backup_path}")
            return True
    except Exception as e:
        print(f"ERROR creating backup: {e}")
        return False


def main():
    """Main function"""
    print("=" * 70)
    print("AIT CMMS Database Configuration Updater")
    print("=" * 70)
    print()

    # Get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    main_file = os.path.join(current_dir, "AIT_CMMS_REV3.py")
    migrate_file = os.path.join(current_dir, "migrate_multiuser.py")

    # Check if files exist
    if not os.path.exists(main_file):
        print(f"ERROR: {main_file} not found!")
        return 1

    if not os.path.exists(migrate_file):
        print(f"ERROR: {migrate_file} not found!")
        return 1

    print("Files found:")
    print(f"  1. {main_file}")
    print(f"  2. {migrate_file}")
    print()

    # Get local IP
    local_ip = get_local_ip()
    print(f"Detected local IP address: {local_ip}")
    print()

    # Ask user for configuration type
    print("Configuration options:")
    print("  1. Localhost (for testing on this computer)")
    print(f"  2. Network IP ({local_ip}) - for multi-user access")
    print("  3. Custom IP address")
    print()

    choice = input("Select option (1-3): ").strip()

    if choice == '1':
        host = 'localhost'
        print("Selected: Localhost")
    elif choice == '2':
        host = local_ip
        print(f"Selected: Network IP ({local_ip})")
    elif choice == '3':
        host = input("Enter custom IP address: ").strip()
        print(f"Selected: Custom IP ({host})")
    else:
        print("Invalid choice. Exiting.")
        return 1

    print()

    # Ask for password
    password = input("Enter PostgreSQL password for 'cmms_user' (default: CMMS_2024_Secure!): ").strip()
    if not password:
        password = "CMMS_2024_Secure!"

    print()
    print("-" * 70)
    print("Configuration summary:")
    print(f"  Host: {host}")
    print(f"  Port: 5432")
    print(f"  Database: ait_cmms")
    print(f"  User: cmms_user")
    print(f"  Password: {'*' * len(password)}")
    print(f"  SSL Mode: prefer")
    print("-" * 70)
    print()

    # Confirm
    confirm = input("Update configuration files? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Operation cancelled.")
        return 0

    print()
    print("Updating files...")
    print()

    # Create backups
    print("Creating backups...")
    backup_file(main_file)
    backup_file(migrate_file)
    print()

    # Update main file
    print("Updating AIT_CMMS_REV3.py...")
    main_content = read_file(main_file)
    if main_content:
        updated_main = update_main_config(main_content, host, password)
        if updated_main:
            if write_file(main_file, updated_main):
                print("✓ AIT_CMMS_REV3.py updated successfully")
            else:
                print("✗ Failed to update AIT_CMMS_REV3.py")
                return 1
        else:
            print("✗ Could not find DB_CONFIG in AIT_CMMS_REV3.py")
            return 1

    # Update migrate file
    print("Updating migrate_multiuser.py...")
    migrate_content = read_file(migrate_file)
    if migrate_content:
        updated_migrate = update_migrate_config(migrate_content, host, password)
        if updated_migrate:
            if write_file(migrate_file, updated_migrate):
                print("✓ migrate_multiuser.py updated successfully")
            else:
                print("✗ Failed to update migrate_multiuser.py")
                return 1
        else:
            print("✗ Could not find DB_CONFIG in migrate_multiuser.py")
            return 1

    print()
    print("=" * 70)
    print("Configuration update completed successfully!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Ensure PostgreSQL is running")
    print("  2. Test connection: psql -U cmms_user -h", host, "-d ait_cmms")
    print("  3. Run the application: python AIT_CMMS_REV3.py")
    print()

    # If network mode, provide employee instructions
    if host != 'localhost':
        print("=" * 70)
        print("EMPLOYEE SETUP INSTRUCTIONS")
        print("=" * 70)
        print()
        print("For employees to connect from other computers:")
        print()
        print("1. Ensure they have Python installed with required packages:")
        print("   pip install psycopg2-binary pillow reportlab")
        print()
        print("2. Copy the entire CMMS folder to their computer")
        print()
        print("3. Tell them the database server IP:", host)
        print()
        print("4. They should be able to run: python AIT_CMMS_REV3.py")
        print()
        print("5. If connection fails, check:")
        print(f"   - Laptop IP is {host}")
        print("   - PostgreSQL is running")
        print("   - Port 5432 is open in firewall")
        print("   - pg_hba.conf allows their IP range")
        print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
