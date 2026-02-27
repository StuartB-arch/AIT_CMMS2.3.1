"""
Skydrol PM Task Module
======================
Manages weekly preventive maintenance for Hydraulic Unit Skydrol fluid
level inspection and top-off.

Responsibilities
----------------
* Ensure hydraulic unit equipment records exist in the CMMS equipment table
  (needed to satisfy the FK constraint on weekly_pm_schedules).
  NOTE: weekly_pm is intentionally left FALSE so the normal PM scheduler
  does NOT pick these units up in its round-robin pool.  All Skydrol-unit
  scheduling is handled exclusively by generate_weekly_skydrol_pm().
* Create / update the Skydrol-specific PM checklist template in pm_templates.
* For every configured hydraulic unit, delete any existing 'Scheduled' weekly
  entry for the requested week and insert a fresh one assigned to a
  *randomly* selected available technician.

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
from datetime import datetime
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
    Manages weekly Skydrol fluid-level check PMs for all configured hydraulic
    units.

    IMPORTANT – scheduling ownership
    ---------------------------------
    Hydraulic unit equipment records are stored in the ``equipment`` table with
    ALL pm-type flags set to FALSE (weekly_pm, monthly_pm, six_month_pm,
    annual_pm).  This keeps them out of the normal PM scheduler's equipment
    pool so they are never assigned via round-robin.  All scheduling for these
    units is performed exclusively by ``generate_weekly_skydrol_pm()``, which
    deletes any existing 'Scheduled' entry for the week and replaces it with a
    freshly randomly-assigned technician on every run.

    Parameters
    ----------
    conn : psycopg2 connection
        Active database connection (same ``self.conn`` object used by the
        main CMMS application).
    """

    PM_TYPE: str = "Weekly"
    ESTIMATED_HOURS: float = 0.5  # ~30 minutes per unit

    def __init__(self, conn):
        self.conn = conn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def setup(self) -> None:
        """
        Idempotent start-up routine.
        Ensures equipment records and PM checklist templates exist.
        Safe to call on every application launch.
        """
        self._ensure_hydraulic_units()
        self._ensure_pm_templates()

    def generate_weekly_skydrol_pm(
        self,
        week_start_str: str,
        available_technicians: List[str],
    ) -> Dict:
        """
        Schedule Skydrol level-check PMs for every hydraulic unit.

        For each unit the function:
          1. Deletes any existing 'Scheduled' (not yet completed) entry for
             the week so the assignment is always freshly randomised.
          2. Inserts a new 'Scheduled' row with a randomly chosen technician.

        Already-completed rows (status != 'Scheduled') are left untouched.

        Parameters
        ----------
        week_start_str : str
            ISO-format week start date, e.g. ``"2025-03-10"`` (Monday).
        available_technicians : list[str]
            Names eligible for random assignment.

        Returns
        -------
        dict
            ``success`` (bool), ``tasks_added`` (int),
            ``assignments`` (list[dict]), ``error`` (str – on failure only)
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

                # Remove any open (not yet completed) schedule for this unit /
                # week so we always emit a fresh random assignment.
                cursor.execute(
                    """
                    DELETE FROM weekly_pm_schedules
                    WHERE week_start_date = %s
                      AND bfm_equipment_no = %s
                      AND pm_type          = %s
                      AND status           = 'Scheduled'
                    """,
                    (week_start_str, bfm_no, self.PM_TYPE),
                )
                deleted = cursor.rowcount
                if deleted:
                    print(
                        f"INFO [Skydrol]: Replaced existing open schedule for "
                        f"{bfm_no} week {week_start_str}."
                    )

                # Randomly select an available technician for this unit.
                technician = random.choice(available_technicians)

                # Always schedule on the Monday of the requested week.
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
                    f"({bfm_no}) \u2192 {technician} on {scheduled_date}"
                )

            self.conn.commit()

            return {
                "success": True,
                "tasks_added": len(assignments),
                "assignments": assignments,
            }

        except Exception as exc:
            try:
                self.conn.rollback()
            except Exception:
                pass
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
        """
        Insert missing hydraulic unit equipment records.

        All PM-type flags (weekly_pm, monthly_pm, six_month_pm, annual_pm)
        are set to FALSE so the normal round-robin scheduler ignores these
        units.  The records exist solely to satisfy the FK constraint on
        weekly_pm_schedules and to supply description / location for the
        schedule display.
        """
        cursor = self.conn.cursor()

        for unit in HYDRAULIC_UNITS:
            bfm_no = unit["bfm_equipment_no"]

            # Use UPSERT: insert if missing, or reset flags if already present
            # so that any accidental weekly_pm=TRUE is corrected.
            cursor.execute(
                """
                INSERT INTO equipment
                    (sap_material_no, bfm_equipment_no, description,
                     tool_id_drawing_no, location,
                     weekly_pm, monthly_pm, six_month_pm, annual_pm,
                     status)
                VALUES (%s, %s, %s, %s, %s,
                        FALSE, FALSE, FALSE, FALSE,
                        'Active')
                ON CONFLICT (bfm_equipment_no) DO UPDATE
                    SET weekly_pm    = FALSE,
                        monthly_pm   = FALSE,
                        six_month_pm = FALSE,
                        annual_pm    = FALSE,
                        status       = 'Active',
                        updated_date = CURRENT_TIMESTAMP
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
                f"INFO [Skydrol]: Equipment record upserted for {bfm_no} "
                f"(weekly_pm=FALSE – managed by Skydrol module only)."
            )

        self.conn.commit()

    def _ensure_pm_templates(self) -> None:
        """Create or update the Skydrol PM checklist template for each unit."""
        cursor = self.conn.cursor()

        # Guard: pm_templates table may not exist on a brand-new installation.
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name   = 'pm_templates'
            )
            """
        )
        row = cursor.fetchone()
        if not (row and row[0]):
            print(
                "INFO [Skydrol]: pm_templates table not yet created – "
                "template will be created on next startup."
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
            template_name = f"Skydrol Level Check - {unit['description']}"

            cursor.execute(
                """
                SELECT id FROM pm_templates
                WHERE bfm_equipment_no = %s AND pm_type = %s
                """,
                (bfm_no, self.PM_TYPE),
            )
            existing = cursor.fetchone()

            if existing:
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
                        existing[0],
                    ),
                )
                print(f"INFO [Skydrol]: Updated PM template for {bfm_no}.")
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
                print(f"INFO [Skydrol]: Created PM template for {bfm_no}.")

        self.conn.commit()
