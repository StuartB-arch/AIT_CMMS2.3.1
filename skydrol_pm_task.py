"""
Skydrol PM Task Module
======================
Manages weekly preventive maintenance for Hydraulic Unit Skydrol fluid
level inspection and top-off.

Responsibilities
----------------
* Ensure hydraulic unit equipment records exist in the CMMS equipment table.
* Create / update the Skydrol-specific PM checklist template in pm_templates.
* Inject a weekly PM entry into weekly_pm_schedules for every configured
  hydraulic unit, each assigned to a *randomly* selected available technician.

Designed to integrate cleanly with the existing AIT CMMS scheduling pipeline:

    from skydrol_pm_task import SkydrolPMTaskManager

    # One-time setup (safe to call every start-up)
    SkydrolPMTaskManager(conn).setup()

    # Called by generate_weekly_assignments() alongside normal PM generation
    skydrol_mgr = SkydrolPMTaskManager(conn)
    skydrol_result = skydrol_mgr.generate_weekly_skydrol_pm(
        week_start_str, available_technicians
    )
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List

# ---------------------------------------------------------------------------
# Hydraulic Unit Configuration
# ---------------------------------------------------------------------------
# Add or remove entries here to match the actual hydraulic units on the floor.
# BFM numbers use the prefix "HYD-UNIT-" to distinguish them from standard
# tooling assets.  SAP numbers are placeholders – update when SAP records are
# created for these units.
# ---------------------------------------------------------------------------
HYDRAULIC_UNITS: List[Dict] = [
    {
        "bfm_equipment_no": "HYD-UNIT-001",
        "sap_material_no": "96099001",
        "description": "HYDRAULIC POWER UNIT - LCS001",
        "tool_id_drawing_no": "HYD-PWR-001",
        "location": "LCS001",
    },
    {
        "bfm_equipment_no": "HYD-UNIT-002",
        "sap_material_no": "96099002",
        "description": "HYDRAULIC POWER UNIT - LCS002",
        "tool_id_drawing_no": "HYD-PWR-002",
        "location": "LCS002",
    },
    {
        "bfm_equipment_no": "HYD-UNIT-003",
        "sap_material_no": "96099003",
        "description": "HYDRAULIC POWER UNIT - LCS030/040",
        "tool_id_drawing_no": "HYD-PWR-003",
        "location": "LCS030/040",
    },
]

# ---------------------------------------------------------------------------
# PM Checklist – Skydrol Level Inspection & Top-Off
# ---------------------------------------------------------------------------
SKYDROL_CHECKLIST: List[str] = [
    "Verify unit is de-energized and hydraulic pressure is at zero before opening any lines.",
    "Inspect all hydraulic lines, fittings, and seals for visible leaks or seepage.",
    "Locate the Skydrol fluid reservoir sight glass or level indicator.",
    "Record the current fluid level status (FULL / LOW / CRITICAL) in the maintenance log.",
    "If level is LOW or CRITICAL, obtain the correct Skydrol grade per the unit nameplate "
    "(LD-4 or LD-5 – do NOT mix grades).",
    "Don required PPE: chemical-resistant gloves, safety glasses/face-shield, and protective apron.",
    "Top off fluid to the FULL mark using a clean, labeled, dedicated Skydrol transfer container.",
    "Re-inspect the sight glass / level indicator to confirm fluid is at the FULL mark.",
    "Inspect the reservoir cap/breather vent – re-torque or replace if damaged.",
    "Check hydraulic filter condition indicator – replace filter element if bypass indicator is active.",
    "Wipe all external surfaces with a clean, lint-free cloth to remove spilled Skydrol.",
    "Dispose of waste fluid, rags, and empty containers in approved hazardous-waste receptacles "
    "per environmental SOP.",
    "Document the quantity of Skydrol added (oz or liters) in the maintenance log.",
    "Note any recurring low-level trends – open a Corrective Maintenance (CM) ticket if more "
    "than 10 % of reservoir capacity was added in a single service event.",
    "Validate maintenance with Date / Technician Stamp / Total Hours.",
    "Confirm all tools, PPE, and materials have been collected and workspace is clean.",
    "Ensure AIT identification sticker is applied and legible on the unit.",
]

SKYDROL_SAFETY_NOTES: str = (
    "WARNING: Skydrol is a fire-resistant phosphate-ester hydraulic fluid and a known skin, "
    "eye, and respiratory irritant. Always wear chemical-resistant gloves, safety glasses or a "
    "full face shield, and a protective apron when handling. In case of skin or eye contact, "
    "flush immediately with large amounts of water for at least 15 minutes and seek medical "
    "attention. Consult the Skydrol Safety Data Sheet (SDS) before performing any service. "
    "Keep containers sealed when not in use to prevent moisture contamination."
)

SKYDROL_SPECIAL_INSTRUCTIONS: str = (
    "1. Confirm fluid type on unit nameplate BEFORE topping off – never mix Skydrol grades.\n"
    "2. Use only dedicated, clearly labeled Skydrol transfer equipment.\n"
    "3. Keep fluid containers sealed when not in use to prevent moisture absorption.\n"
    "4. If more than 10 % of reservoir capacity is added in a single service, escalate for "
    "root-cause investigation and open a CM ticket.\n"
    "5. Refer to the OEM hydraulic unit manual for system pressure specifications and reservoir "
    "capacity.\n"
    "6. Skydrol spills are an environmental hazard – follow site spill-response procedures."
)

# ---------------------------------------------------------------------------
# Manager Class
# ---------------------------------------------------------------------------

class SkydrolPMTaskManager:
    """
    Manages weekly Skydrol fluid-level check PMs for all configured hydraulic units.

    Parameters
    ----------
    conn : psycopg2 connection
        Active database connection (same object used by the main CMMS).
    """

    PM_TYPE: str = "Weekly"
    ESTIMATED_HOURS: float = 0.5  # Approximately 30 minutes per unit

    def __init__(self, conn):
        self.conn = conn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def setup(self) -> None:
        """
        One-time idempotent setup.
        Ensures hydraulic unit equipment records and PM templates exist in the
        database.  Safe to call on every application start-up.
        """
        self._ensure_hydraulic_units()
        self._ensure_pm_templates()

    def generate_weekly_skydrol_pm(
        self,
        week_start_str: str,
        available_technicians: List[str],
    ) -> Dict:
        """
        Insert Skydrol level-check PM tasks for each hydraulic unit into
        ``weekly_pm_schedules`` for the given week.

        Each unit is assigned to a **randomly** selected technician from
        ``available_technicians``, independent of the technician chosen for any
        other unit so that multiple technicians can share the workload.

        The operation is idempotent: if a Skydrol PM for a given unit and week
        already exists in the schedule it is left unchanged.

        Parameters
        ----------
        week_start_str : str
            ISO-format week start date, e.g. ``"2025-03-10"`` (Monday).
        available_technicians : list[str]
            Names of technicians eligible for assignment (already filtered for
            any exclusions the user has applied in the UI).

        Returns
        -------
        dict with keys:
            ``success`` (bool), ``tasks_added`` (int),
            ``assignments`` (list[dict]), ``error`` (str, on failure only)
        """
        if not available_technicians:
            return {
                "success": False,
                "tasks_added": 0,
                "assignments": [],
                "error": "No technicians available for Skydrol PM assignment.",
            }

        try:
            week_start_dt = datetime.strptime(week_start_str, "%Y-%m-%d")
            assignments: List[Dict] = []
            cursor = self.conn.cursor()

            for unit in HYDRAULIC_UNITS:
                bfm_no = unit["bfm_equipment_no"]

                # Idempotency check – skip if already scheduled this week
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM weekly_pm_schedules
                    WHERE week_start_date = %s
                      AND bfm_equipment_no = %s
                      AND pm_type = %s
                    """,
                    (week_start_str, bfm_no, self.PM_TYPE),
                )
                row = cursor.fetchone()
                existing_count = row[0] if row else 0
                if existing_count > 0:
                    print(
                        f"INFO [Skydrol]: {bfm_no} already scheduled for week "
                        f"{week_start_str} – skipping."
                    )
                    continue

                # Each unit gets its own independent random technician draw
                technician = random.choice(available_technicians)

                # Schedule on the Monday of the week (first day = most visibility)
                scheduled_date = week_start_dt.strftime("%Y-%m-%d")

                cursor.execute(
                    """
                    INSERT INTO weekly_pm_schedules
                        (week_start_date, bfm_equipment_no, pm_type,
                         assigned_technician, scheduled_date, status)
                    VALUES (%s, %s, %s, %s, %s, 'Scheduled')
                    """,
                    (
                        week_start_str,
                        bfm_no,
                        self.PM_TYPE,
                        technician,
                        scheduled_date,
                    ),
                )

                assignments.append(
                    {
                        "bfm_no": bfm_no,
                        "description": unit["description"],
                        "pm_type": self.PM_TYPE,
                        "technician": technician,
                        "scheduled_date": scheduled_date,
                        "location": unit["location"],
                        "task": "Skydrol fluid level inspection & top-off",
                    }
                )

                print(
                    f"INFO [Skydrol]: Scheduled '{unit['description']}' "
                    f"({bfm_no}) → {technician} for {scheduled_date}"
                )

            self.conn.commit()

            return {
                "success": True,
                "tasks_added": len(assignments),
                "assignments": assignments,
            }

        except Exception as exc:
            self.conn.rollback()
            import traceback

            traceback.print_exc()
            return {
                "success": False,
                "tasks_added": 0,
                "assignments": [],
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_hydraulic_units(self) -> None:
        """Insert hydraulic unit equipment records that are missing, or update
        the weekly_pm flag on existing records."""
        cursor = self.conn.cursor()

        for unit in HYDRAULIC_UNITS:
            bfm_no = unit["bfm_equipment_no"]

            cursor.execute(
                "SELECT id FROM equipment WHERE bfm_equipment_no = %s",
                (bfm_no,),
            )
            existing = cursor.fetchone()

            if existing:
                # Record exists – ensure weekly_pm flag is set and unit is active
                cursor.execute(
                    """
                    UPDATE equipment
                    SET weekly_pm = TRUE,
                        status = 'Active',
                        updated_date = CURRENT_TIMESTAMP
                    WHERE bfm_equipment_no = %s
                    """,
                    (bfm_no,),
                )
                print(
                    f"INFO [Skydrol]: Equipment {bfm_no} exists – ensured weekly_pm=TRUE."
                )
            else:
                # Insert a new equipment record for this hydraulic unit
                cursor.execute(
                    """
                    INSERT INTO equipment
                        (sap_material_no, bfm_equipment_no, description,
                         tool_id_drawing_no, location,
                         weekly_pm, monthly_pm, six_month_pm, annual_pm,
                         status)
                    VALUES (%s, %s, %s, %s, %s,
                            TRUE, FALSE, FALSE, FALSE,
                            'Active')
                    """,
                    (
                        unit["sap_material_no"],
                        unit["bfm_equipment_no"],
                        unit["description"],
                        unit["tool_id_drawing_no"],
                        unit["location"],
                    ),
                )
                print(
                    f"INFO [Skydrol]: Inserted new equipment record for {bfm_no} "
                    f"({unit['description']})."
                )

        self.conn.commit()

    def _ensure_pm_templates(self) -> None:
        """Create or update the Skydrol PM checklist template for every
        configured hydraulic unit."""
        cursor = self.conn.cursor()

        # Guard: pm_templates table might not exist on very first start-up
        # before init_pm_templates_database() runs.  Skip silently if so.
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'pm_templates'
            )
            """
        )
        row = cursor.fetchone()
        table_exists = row[0] if row else False
        if not table_exists:
            print(
                "INFO [Skydrol]: pm_templates table not yet created – "
                "template setup will run on next startup."
            )
            return

        checklist_json = json.dumps(
            [
                {"step": idx + 1, "description": item}
                for idx, item in enumerate(SKYDROL_CHECKLIST)
            ]
        )

        for unit in HYDRAULIC_UNITS:
            bfm_no = unit["bfm_equipment_no"]
            template_name = f"Skydrol Level Check – {unit['description']}"

            cursor.execute(
                """
                SELECT id FROM pm_templates
                WHERE bfm_equipment_no = %s AND pm_type = %s
                """,
                (bfm_no, self.PM_TYPE),
            )
            existing_template = cursor.fetchone()

            if existing_template:
                cursor.execute(
                    """
                    UPDATE pm_templates
                    SET template_name        = %s,
                        checklist_items      = %s,
                        special_instructions = %s,
                        safety_notes         = %s,
                        estimated_hours      = %s,
                        updated_date         = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        template_name,
                        checklist_json,
                        SKYDROL_SPECIAL_INSTRUCTIONS,
                        SKYDROL_SAFETY_NOTES,
                        self.ESTIMATED_HOURS,
                        existing_template[0],
                    ),
                )
                print(
                    f"INFO [Skydrol]: Updated PM template for {bfm_no}."
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO pm_templates
                        (bfm_equipment_no, template_name, pm_type,
                         checklist_items, special_instructions,
                         safety_notes, estimated_hours)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        bfm_no,
                        template_name,
                        self.PM_TYPE,
                        checklist_json,
                        SKYDROL_SPECIAL_INSTRUCTIONS,
                        SKYDROL_SAFETY_NOTES,
                        self.ESTIMATED_HOURS,
                    ),
                )
                print(
                    f"INFO [Skydrol]: Created PM template for {bfm_no}."
                )

        self.conn.commit()
