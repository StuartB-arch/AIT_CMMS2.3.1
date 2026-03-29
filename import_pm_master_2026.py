#!/usr/bin/env python3
"""
PM Master 2026 Import Script
Imports / updates all equipment records from PM_MASTER_2026.csv into the CMMS database.

Rules:
  - BFM Equipment No is the unique key (primary key in the database).
  - Duplicate BFM entries in the CSV: the Active entry wins; if all have the
    same status, the first occurrence wins.
  - SAP numbers are NOT unique (same SAP can map to multiple BFM numbers for
    the same tool type at different locations). No deduplication is done on SAP.
  - Existing database records are UPDATED with the latest data from the CSV.
  - Brand-new BFM numbers are INSERTED.
  - Status is preserved exactly as in the CSV:
      "Active"       → only these assets will be scheduled by pm_scheduler.py
      "Deactivated"  → stored but excluded from scheduling
      "Cannot Find"  → stored but excluded from scheduling
  - PM scheduling priority (P1/P2/P3/P4) is unchanged: assets in
    PM_LIST_A220_1.csv = P1, PM_LIST_A220_2.csv = P2, PM_LIST_A220_3.csv = P3,
    all others default to P4 (priority 99 in the scheduler).
"""

import csv
import os
import sys
from datetime import datetime
from collections import defaultdict

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Database configuration – adjust to match your deployment
# ---------------------------------------------------------------------------
# The script will try the configs in order and use the first that connects.
DB_CONFIGS = [
    # Local PostgreSQL (after migration from NEON)
    {
        'host': 'localhost',
        'port': 5432,
        'database': 'ait_cmms',
        'user': 'cmms_user',
        'password': 'CMMS_2024_Secure!',
        'sslmode': 'prefer',
    },
    # NEON Cloud (original deployment)
    {
        'host': 'ep-tiny-paper-ad8glt26-pooler.c-2.us-east-1.aws.neon.tech',
        'port': 5432,
        'database': 'neondb',
        'user': 'neondb_owner',
        'password': 'npg_2Nm6hyPVWiIH',
        'sslmode': 'require',
    },
]

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PM_MASTER_2026.csv')

# Status values accepted by the scheduler
VALID_STATUSES = {'Active', 'Deactivated', 'Cannot Find'}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_date(date_str: str):
    """Return a datetime.date or None for common date formats in the CSV."""
    if not date_str or not date_str.strip():
        return None
    s = date_str.strip()
    # Strip trailing time component like " 0:00"
    if ' ' in s:
        s = s.split(' ')[0]
    for fmt in ('%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    print(f"  WARNING: Could not parse date '{date_str}'")
    return None


def parse_bool(val: str) -> bool:
    return val.strip().upper() == 'TRUE'


def connect_db():
    """Try each DB config in order; return first successful connection."""
    for cfg in DB_CONFIGS:
        try:
            conn = psycopg2.connect(
                host=cfg['host'],
                port=cfg['port'],
                database=cfg['database'],
                user=cfg['user'],
                password=cfg['password'],
                sslmode=cfg.get('sslmode', 'prefer'),
                connect_timeout=30,
            )
            print(f"Connected to database at {cfg['host']}/{cfg['database']}")
            return conn
        except psycopg2.OperationalError as e:
            print(f"Could not connect to {cfg['host']}: {e}")
    print("ERROR: Could not connect to any database. Check your DB_CONFIGS.")
    sys.exit(1)


def get_db_columns(conn, table='equipment'):
    """Return the set of column names that actually exist in the table."""
    cur = conn.cursor()
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table,),
    )
    return {row[0] for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# CSV parsing and deduplication
# ---------------------------------------------------------------------------

def load_and_deduplicate_csv(filepath: str):
    """
    Read PM_MASTER_2026.csv, deduplicate on BFM Equipment No.

    Deduplication rules:
      1. If the BFM has both Active and non-Active entries → keep Active.
      2. If all entries for a BFM share the same status → keep the first one
         (lowest CSV row ID, which is generally the most current entry at the
         top of the master list).

    Returns a list of deduplicated row dicts and a summary dict.
    """
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    print(f"CSV rows read (excluding header): {len(all_rows)}")

    # Group by BFM
    bfm_groups = defaultdict(list)
    for row in all_rows:
        bfm = row['BFM Equipment No'].strip()
        if not bfm:
            continue  # skip blank BFM rows (none expected per analysis)
        bfm_groups[bfm].append(row)

    deduped = []
    dup_count = 0
    active_wins = 0

    for bfm, group in bfm_groups.items():
        if len(group) == 1:
            deduped.append(group[0])
            continue

        dup_count += 1
        statuses = [r['Status'].strip() for r in group]

        if 'Active' in statuses and len(set(statuses)) > 1:
            # Mixed statuses: prefer Active
            chosen = next(r for r in group if r['Status'].strip() == 'Active')
            active_wins += 1
        else:
            # All same status: use first entry (lowest ID = top of file)
            chosen = group[0]

        deduped.append(chosen)

    summary = {
        'total_csv_rows': len(all_rows),
        'unique_bfm_count': len(deduped),
        'duplicate_groups': dup_count,
        'active_wins': active_wins,
    }
    return deduped, summary


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

def fetch_existing_bfms(conn):
    """Return a set of BFM numbers already in the equipment table."""
    cur = conn.cursor()
    cur.execute("SELECT bfm_equipment_no FROM equipment")
    return {row[0] for row in cur.fetchall()}


def upsert_equipment(conn, rows, existing_bfms, db_columns):
    """
    INSERT new equipment or UPDATE existing equipment using data from the CSV.

    Returns counts: inserted, updated, skipped (bad status), errors.
    """
    inserted = 0
    updated = 0
    skipped = 0
    errors = 0

    # Determine which optional columns actually exist in this database instance
    has_sap = 'sap_material_no' in db_columns
    has_six_month_pm = 'six_month_pm' in db_columns
    has_last_six_month = 'last_six_month_pm' in db_columns
    has_weekly_pm = 'weekly_pm' in db_columns
    has_last_weekly = 'last_weekly_pm' in db_columns
    has_next_annual = 'next_annual_pm' in db_columns
    has_location = 'location' in db_columns
    has_tool_id = 'tool_id' in db_columns

    cur = conn.cursor()

    for row in rows:
        bfm = row['BFM Equipment No'].strip()
        status = row['Status'].strip()

        if status not in VALID_STATUSES:
            print(f"  SKIP BFM {bfm}: unknown status '{status}'")
            skipped += 1
            continue

        sap = row.get('SAP Material No', '').strip()
        description = row.get('Description', '').strip()
        location = row.get('Location', '').strip()
        tool_id = row.get('Tool ID/Drawing No', '').strip()

        monthly_pm = parse_bool(row.get('Monthly PM', 'FALSE'))
        six_month_pm = parse_bool(row.get('Six Month PM', 'FALSE'))
        annual_pm = parse_bool(row.get('Annual PM', 'FALSE'))

        last_monthly = parse_date(row.get('Last Monthly PM', ''))
        last_six_month = parse_date(row.get('Last Six Month PM', ''))
        last_annual = parse_date(row.get('Last Annual PM', ''))
        next_annual = parse_date(row.get('Next Annual PM', ''))

        try:
            if bfm in existing_bfms:
                # ---- UPDATE ------------------------------------------------
                set_parts = [
                    "description = %s",
                    "monthly_pm = %s",
                    "annual_pm = %s",
                    "status = %s",
                ]
                params = [description, monthly_pm, annual_pm, status]

                if has_sap:
                    set_parts.append("sap_material_no = %s")
                    params.append(sap)
                if has_location:
                    set_parts.append("location = %s")
                    params.append(location)
                if has_tool_id:
                    set_parts.append("tool_id = %s")
                    params.append(tool_id)
                if has_six_month_pm:
                    set_parts.append("six_month_pm = %s")
                    params.append(six_month_pm)
                if has_last_six_month and last_six_month is not None:
                    set_parts.append("last_six_month_pm = %s")
                    params.append(last_six_month)
                if 'last_monthly_pm' in db_columns and last_monthly is not None:
                    set_parts.append("last_monthly_pm = %s")
                    params.append(last_monthly)
                if 'last_annual_pm' in db_columns and last_annual is not None:
                    set_parts.append("last_annual_pm = %s")
                    params.append(last_annual)
                if has_next_annual and next_annual is not None:
                    set_parts.append("next_annual_pm = %s")
                    params.append(next_annual)

                params.append(bfm)
                sql = f"UPDATE equipment SET {', '.join(set_parts)} WHERE bfm_equipment_no = %s"
                cur.execute(sql, params)
                updated += 1

            else:
                # ---- INSERT ------------------------------------------------
                cols = ['bfm_equipment_no', 'description', 'monthly_pm', 'annual_pm', 'status']
                vals = [bfm, description, monthly_pm, annual_pm, status]

                if has_sap:
                    cols.append('sap_material_no')
                    vals.append(sap)
                if has_location:
                    cols.append('location')
                    vals.append(location)
                if has_tool_id:
                    cols.append('tool_id')
                    vals.append(tool_id)
                if has_six_month_pm:
                    cols.append('six_month_pm')
                    vals.append(six_month_pm)
                if has_weekly_pm:
                    cols.append('weekly_pm')
                    vals.append(False)   # CSV has no weekly PM column; default False
                if 'last_monthly_pm' in db_columns and last_monthly is not None:
                    cols.append('last_monthly_pm')
                    vals.append(last_monthly)
                if has_last_six_month and last_six_month is not None:
                    cols.append('last_six_month_pm')
                    vals.append(last_six_month)
                if 'last_annual_pm' in db_columns and last_annual is not None:
                    cols.append('last_annual_pm')
                    vals.append(last_annual)
                if has_next_annual and next_annual is not None:
                    cols.append('next_annual_pm')
                    vals.append(next_annual)

                placeholders = ', '.join(['%s'] * len(vals))
                sql = f"INSERT INTO equipment ({', '.join(cols)}) VALUES ({placeholders})"
                cur.execute(sql, vals)
                inserted += 1

        except Exception as e:
            print(f"  ERROR on BFM {bfm}: {e}")
            conn.rollback()
            errors += 1
            continue

    conn.commit()
    cur.close()
    return inserted, updated, skipped, errors


# ---------------------------------------------------------------------------
# Deactivated / Cannot Find sync into auxiliary tables (if they exist)
# ---------------------------------------------------------------------------

def sync_auxiliary_tables(conn, rows, db_columns_all):
    """
    If the database has cannot_find_assets or deactivated_assets tables,
    ensure that any Cannot Find / Deactivated BFMs from PM_MASTER_2026 are
    recorded there so the scheduler's exclusion queries still work correctly.
    """
    cur = conn.cursor()

    # Check which auxiliary tables exist
    cur.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    existing_tables = {row[0] for row in cur.fetchall()}

    synced_cf = 0
    synced_da = 0

    for row in rows:
        bfm = row['BFM Equipment No'].strip()
        status = row['Status'].strip()

        if status == 'Cannot Find' and 'cannot_find_assets' in existing_tables:
            cur.execute(
                "SELECT 1 FROM cannot_find_assets WHERE bfm_equipment_no = %s", (bfm,)
            )
            if not cur.fetchone():
                try:
                    cur.execute(
                        "INSERT INTO cannot_find_assets (bfm_equipment_no, status) VALUES (%s, %s)",
                        (bfm, 'Missing')
                    )
                    synced_cf += 1
                except Exception:
                    conn.rollback()

        elif status == 'Deactivated' and 'deactivated_assets' in existing_tables:
            cur.execute(
                "SELECT 1 FROM deactivated_assets WHERE bfm_equipment_no = %s", (bfm,)
            )
            if not cur.fetchone():
                try:
                    cur.execute(
                        "INSERT INTO deactivated_assets (bfm_equipment_no) VALUES (%s)",
                        (bfm,)
                    )
                    synced_da += 1
                except Exception:
                    conn.rollback()

    conn.commit()
    cur.close()

    if synced_cf or synced_da:
        print(f"  Auxiliary tables: added {synced_cf} Cannot Find, {synced_da} Deactivated entries")


# ---------------------------------------------------------------------------
# Post-import validation report
# ---------------------------------------------------------------------------

def print_validation_report(conn):
    cur = conn.cursor()
    print("\n" + "=" * 60)
    print("POST-IMPORT VALIDATION")
    print("=" * 60)

    cur.execute("SELECT COUNT(*) FROM equipment")
    print(f"Total equipment records: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM equipment WHERE status = 'Active'")
    print(f"Active equipment: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM equipment WHERE status = 'Deactivated'")
    print(f"Deactivated equipment: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM equipment WHERE status = 'Cannot Find'")
    print(f"Cannot Find equipment: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM equipment WHERE status = 'Active' AND monthly_pm = TRUE")
    print(f"Active assets with Monthly PM: {cur.fetchone()[0]}")

    # Only count six_month_pm if the column exists
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'equipment' AND column_name = 'six_month_pm'"
    )
    if cur.fetchone():
        cur.execute("SELECT COUNT(*) FROM equipment WHERE status = 'Active' AND six_month_pm = TRUE")
        print(f"Active assets with Six Month PM: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM equipment WHERE status = 'Active' AND annual_pm = TRUE")
    print(f"Active assets with Annual PM: {cur.fetchone()[0]}")

    # Duplicate BFM check (should always be 0)
    cur.execute(
        "SELECT bfm_equipment_no, COUNT(*) c FROM equipment "
        "GROUP BY bfm_equipment_no HAVING COUNT(*) > 1"
    )
    dups = cur.fetchall()
    if dups:
        print(f"\nWARNING: {len(dups)} duplicate BFM numbers found in database:")
        for bfm, cnt in dups[:10]:
            print(f"  BFM {bfm}: {cnt} rows")
    else:
        print("\nNo duplicate BFM numbers in database. ✓")

    cur.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("AIT CMMS – PM Master 2026 Import")
    print("=" * 60)

    # 1. Parse and deduplicate CSV
    print(f"\nReading: {CSV_FILE}")
    rows, csv_summary = load_and_deduplicate_csv(CSV_FILE)

    print(f"\nCSV Summary:")
    print(f"  Total CSV rows           : {csv_summary['total_csv_rows']}")
    print(f"  Unique BFM numbers       : {csv_summary['unique_bfm_count']}")
    print(f"  Duplicate BFM groups     : {csv_summary['duplicate_groups']}")
    print(f"  Active-wins resolutions  : {csv_summary['active_wins']}")

    # Status breakdown of deduplicated rows
    status_counts = defaultdict(int)
    for r in rows:
        status_counts[r['Status'].strip()] += 1
    print(f"\nDeduplicated status breakdown:")
    for s, c in sorted(status_counts.items()):
        print(f"  {s}: {c}")

    # 2. Connect to database
    print("\nConnecting to database...")
    conn = connect_db()

    # 3. Discover actual table columns (handles schema variations)
    db_columns = get_db_columns(conn)
    print(f"Equipment table columns found: {len(db_columns)}")

    # 4. Fetch existing BFMs
    existing_bfms = fetch_existing_bfms(conn)
    print(f"Existing equipment records in DB: {len(existing_bfms)}")

    # 5. Calculate what will happen
    new_bfms = [r for r in rows if r['BFM Equipment No'].strip() not in existing_bfms]
    existing_in_csv = [r for r in rows if r['BFM Equipment No'].strip() in existing_bfms]
    print(f"\nImport plan:")
    print(f"  Records to INSERT (new)  : {len(new_bfms)}")
    print(f"  Records to UPDATE (exist): {len(existing_in_csv)}")

    # 6. Upsert
    print("\nImporting...")
    inserted, updated, skipped, errors = upsert_equipment(conn, rows, existing_bfms, db_columns)

    # 7. Sync auxiliary tables
    sync_auxiliary_tables(conn, rows, db_columns)

    # 8. Results
    print("\n" + "=" * 60)
    print("IMPORT RESULTS")
    print("=" * 60)
    print(f"  Inserted (new records) : {inserted}")
    print(f"  Updated (existing)     : {updated}")
    print(f"  Skipped (bad status)   : {skipped}")
    print(f"  Errors                 : {errors}")

    # 9. Validation report
    print_validation_report(conn)

    conn.close()

    print("\n" + "=" * 60)
    print("PM Master 2026 import complete.")
    print("=" * 60)
    print("""
Scheduling notes:
  • Only 'Active' status assets will be included in PM schedules.
  • Priority order is unchanged:
      P1 = PM_LIST_A220_1.csv assets   (highest urgency)
      P2 = PM_LIST_A220_2.csv assets
      P3 = PM_LIST_A220_3.csv assets
      P4 = all other Active assets     (default priority 99)
  • The weekly scheduler (pm_scheduler.py) requires no code changes;
    it already filters on status = 'Active' and respects the priority files.
""")


if __name__ == '__main__':
    main()
