"""
Vynda — Compliance Monitor
───────────────────────────
Scans the entire agency for compliance issues and fires alerts.
Runs automatically on a schedule (daily) or manually.

What it monitors:
  1. NOA (Notice of Admission) — must be filed within 5 days of admission
  2. LUPA Risk — patients behind on visit pace (revenue at risk)
  3. Credential Expiry — license, CPR, TB test expiring within 90 days
  4. EVV Exceptions — visits without check-in/check-out
  5. Authorization Exhaustion — visits approaching auth limit
  6. Missed Visits — scheduled visits that weren't completed
  7. Episode Ending — patients within 7 days of episode end

Usage:
    cd backend
    python compliance.py           # run full scan
    python compliance.py --report  # print detailed report only, don't write to DB
"""

import os
import sys
import argparse
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
except Exception as e:
    print(f"❌ Supabase connection failed: {e}")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# ALERT BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_alert(
    agency_id: str,
    event_type: str,
    severity: str,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    description: str,
    due_date: str = None,
) -> dict:
    return {
        "agency_id":   agency_id,
        "event_type":  event_type,
        "severity":    severity,
        "entity_type": entity_type,
        "entity_id":   entity_id,
        "entity_name": entity_name,
        "description": description,
        "due_date":    due_date,
        "is_resolved": False,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SCAN FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def scan_noa(agency_id: str, today: date) -> list[dict]:
    """
    NOA must be filed within 5 days of admission.
    Late or missing NOA = Medicare claim denial.
    """
    alerts = []

    patients = supabase.table("patients")\
        .select("id, first_name, last_name, admission_date, noa_filed, noa_date")\
        .eq("agency_id", agency_id)\
        .eq("status", 1)\
        .eq("noa_filed", False)\
        .execute()

    for pt in (patients.data or []):
        admission_str = pt.get("admission_date")
        if not admission_str:
            continue

        admission = date.fromisoformat(admission_str)
        noa_due = admission + timedelta(days=5)
        days_until_due = (noa_due - today).days
        name = f"{pt['first_name']} {pt['last_name']}"

        if days_until_due < 0:
            # Already late
            alerts.append(build_alert(
                agency_id, "noa_due", "critical",
                "patient", pt["id"], name,
                f"⛔ NOA OVERDUE — {name}. Was due {noa_due.strftime('%b %d')} ({abs(days_until_due)} days ago). Claim will be denied.",
                str(noa_due),
            ))
        elif days_until_due <= 2:
            alerts.append(build_alert(
                agency_id, "noa_due", "urgent",
                "patient", pt["id"], name,
                f"🚨 NOA due in {days_until_due} day{'s' if days_until_due != 1 else ''} — {name}. Due {noa_due.strftime('%b %d')}. File immediately.",
                str(noa_due),
            ))
        elif days_until_due <= 5:
            alerts.append(build_alert(
                agency_id, "noa_due", "warning",
                "patient", pt["id"], name,
                f"⚠️ NOA due in {days_until_due} days — {name}. Due {noa_due.strftime('%b %d')}.",
                str(noa_due),
            ))

    return alerts


def scan_lupa_risk(agency_id: str, today: date) -> list[dict]:
    """
    LUPA = Low Utilization Payment Adjustment.
    If patient doesn't get enough visits in a 30-day period,
    Medicare cuts the payment — sometimes by 50%+.
    """
    alerts = []

    patients = supabase.table("patients")\
        .select("id, first_name, last_name, visits_per_week, visits_this_episode, lupa_threshold, benefit_period_end, benefit_period_start, pdgm_group, primary_payor_name")\
        .eq("agency_id", agency_id)\
        .eq("status", 1)\
        .execute()

    for pt in (patients.data or []):
        benefit_end_str = pt.get("benefit_period_end")
        benefit_start_str = pt.get("benefit_period_start")
        if not benefit_end_str or not benefit_start_str:
            continue

        end_date = date.fromisoformat(benefit_end_str)
        start_date = date.fromisoformat(benefit_start_str)
        days_left = (end_date - today).days
        days_total = (end_date - start_date).days or 60
        days_elapsed = (today - start_date).days

        if days_left < 0:
            continue  # episode over

        visits_per_week = pt.get("visits_per_week", 3)
        visits_done = pt.get("visits_this_episode", 0)
        lupa_threshold = pt.get("lupa_threshold", 2)
        weeks_elapsed = days_elapsed / 7
        expected = int(visits_per_week * weeks_elapsed)
        shortfall = max(0, expected - visits_done)
        name = f"{pt['first_name']} {pt['last_name']}"

        if shortfall <= 0:
            continue

        # Calculate revenue at risk (PDGM base rate ~$2,038 per 60-day episode)
        base_rate = 2038
        lupa_rate = base_rate * 0.35  # LUPA typically pays ~35% of full rate
        revenue_at_risk = round(base_rate - lupa_rate, 2)

        if shortfall >= lupa_threshold * 2:
            severity = "critical"
            emoji = "⛔"
        elif shortfall >= lupa_threshold:
            severity = "urgent"
            emoji = "🚨"
        else:
            severity = "warning"
            emoji = "⚠️"

        alerts.append(build_alert(
            agency_id, "lupa_risk", severity,
            "patient", pt["id"], name,
            f"{emoji} LUPA Risk — {name} is {shortfall} visits behind pace. "
            f"{days_left} days left in episode. "
            f"${revenue_at_risk:,.0f} at risk. ({pt.get('pdgm_group','')})",
            str(end_date),
        ))

    return alerts


def scan_credentials(agency_id: str, today: date) -> list[dict]:
    """
    Scan all caregiver credentials for expiry within 90 days.
    Expired credentials = can't see patients = scheduling gaps.
    """
    alerts = []

    creds = supabase.table("caregiver_credentials")\
        .select("*, caregivers!inner(id, first_name, last_name, discipline, agency_id)")\
        .eq("caregivers.agency_id", agency_id)\
        .eq("is_active", True)\
        .execute()

    for cred in (creds.data or []):
        expiry_str = cred.get("expiry_date")
        if not expiry_str:
            continue

        expiry = date.fromisoformat(expiry_str)
        days_left = (expiry - today).days
        caregiver = cred.get("caregivers", {})
        name = f"{caregiver.get('first_name','')} {caregiver.get('last_name','')}".strip()
        disc = caregiver.get("discipline", "")
        cred_type = cred["credential_type"].replace("_", " ").title()

        if days_left < 0:
            alerts.append(build_alert(
                agency_id, "credential_expiry", "critical",
                "caregiver", caregiver.get("id"), name,
                f"⛔ EXPIRED — {name} ({disc}) {cred_type} expired {abs(days_left)} days ago. Cannot see patients.",
                expiry_str,
            ))
        elif days_left <= 14:
            alerts.append(build_alert(
                agency_id, "credential_expiry", "urgent",
                "caregiver", caregiver.get("id"), name,
                f"🚨 {name} ({disc}) {cred_type} expires in {days_left} days. Renew immediately.",
                expiry_str,
            ))
        elif days_left <= 30:
            alerts.append(build_alert(
                agency_id, "credential_expiry", "urgent",
                "caregiver", caregiver.get("id"), name,
                f"⚠️ {name} ({disc}) {cred_type} expires in {days_left} days.",
                expiry_str,
            ))
        elif days_left <= 90:
            alerts.append(build_alert(
                agency_id, "credential_expiry", "warning",
                "caregiver", caregiver.get("id"), name,
                f"📋 {name} ({disc}) {cred_type} expires in {days_left} days. Schedule renewal.",
                expiry_str,
            ))

    return alerts


def scan_evv_exceptions(agency_id: str, today: date) -> list[dict]:
    """
    EVV (Electronic Visit Verification) — federal mandate.
    Every visit must have GPS check-in and check-out.
    Missing EVV = compliance violation + potential payment denial.
    """
    alerts = []

    # Look at completed visits from last 3 days missing EVV
    since = str(today - timedelta(days=3))
    schedules = supabase.table("schedules")\
        .select("id, visit_date, discipline, evv_check_in, evv_check_out, evv_status, patients(first_name, last_name), caregivers(first_name, last_name)")\
        .eq("agency_id", agency_id)\
        .eq("status", "completed")\
        .neq("evv_status", "verified")\
        .gte("visit_date", since)\
        .execute()

    for s in (schedules.data or []):
        patient = s.get("patients") or {}
        caregiver = s.get("caregivers") or {}
        pt_name = f"{patient.get('first_name','')} {patient.get('last_name','')}".strip()
        cg_name = f"{caregiver.get('first_name','')} {caregiver.get('last_name','')}".strip()
        visit_date = s.get("visit_date", "")

        missing = []
        if not s.get("evv_check_in"):
            missing.append("check-in")
        if not s.get("evv_check_out"):
            missing.append("check-out")

        if missing:
            alerts.append(build_alert(
                agency_id, "evv_exception", "warning",
                "patient", None, pt_name,
                f"⚠️ EVV missing {' and '.join(missing)} — {pt_name} visit on {visit_date} by {cg_name}. Fix before billing.",
                visit_date,
            ))

    return alerts


def scan_auth_exhaustion(agency_id: str, today: date) -> list[dict]:
    """
    Authorization exhaustion — if visits_used approaches visits_approved,
    need to request a new auth before it runs out.
    """
    alerts = []

    auths = supabase.table("authorizations")\
        .select("*, patients(first_name, last_name)")\
        .eq("agency_id", agency_id)\
        .eq("status", "active")\
        .execute()

    for auth in (auths.data or []):
        approved = auth.get("visits_approved") or 0
        used = auth.get("visits_used") or 0
        if approved == 0:
            continue

        utilization = used / approved
        patient = auth.get("patients") or {}
        name = f"{patient.get('first_name','')} {patient.get('last_name','')}".strip()
        remaining = approved - used
        end_date = auth.get("end_date", "")

        if utilization >= 1.0:
            alerts.append(build_alert(
                agency_id, "auth_exhausted", "critical",
                "patient", auth.get("patient_id"), name,
                f"⛔ AUTH EXHAUSTED — {name} has used all {approved} authorized {auth.get('discipline','')} visits. Request new auth immediately.",
                end_date,
            ))
        elif utilization >= 0.85:
            alerts.append(build_alert(
                agency_id, "auth_exhausted", "urgent",
                "patient", auth.get("patient_id"), name,
                f"🚨 Auth nearly exhausted — {name} has {remaining} {auth.get('discipline','')} visits remaining of {approved} authorized.",
                end_date,
            ))
        elif utilization >= 0.70:
            alerts.append(build_alert(
                agency_id, "auth_exhausted", "warning",
                "patient", auth.get("patient_id"), name,
                f"⚠️ Auth at {int(utilization*100)}% — {name} has {remaining} {auth.get('discipline','')} visits remaining. Request renewal soon.",
                end_date,
            ))

    return alerts


def scan_missed_visits(agency_id: str, today: date) -> list[dict]:
    """Scheduled visits that were never marked completed."""
    alerts = []

    yesterday = str(today - timedelta(days=1))
    missed = supabase.table("schedules")\
        .select("id, visit_date, discipline, patients(id, first_name, last_name), caregivers(first_name, last_name)")\
        .eq("agency_id", agency_id)\
        .eq("status", "scheduled")\
        .lt("visit_date", str(today))\
        .gte("visit_date", yesterday)\
        .execute()

    for s in (missed.data or []):
        patient = s.get("patients") or {}
        caregiver = s.get("caregivers") or {}
        pt_name = f"{patient.get('first_name','')} {patient.get('last_name','')}".strip()
        cg_name = f"{caregiver.get('first_name','')} {caregiver.get('last_name','')}".strip()

        alerts.append(build_alert(
            agency_id, "missed_visit", "urgent",
            "patient", patient.get("id"), pt_name,
            f"🚨 Missed visit — {pt_name} had a {s.get('discipline','')} visit on {s.get('visit_date','')} with {cg_name} that was never completed.",
            s.get("visit_date"),
        ))

    return alerts


def scan_episode_endings(agency_id: str, today: date) -> list[dict]:
    """Patients whose episode ends within 7 days — need recertification or discharge."""
    alerts = []

    patients = supabase.table("patients")\
        .select("id, first_name, last_name, benefit_period_end, pdgm_group, attending_physician_name")\
        .eq("agency_id", agency_id)\
        .eq("status", 1)\
        .execute()

    for pt in (patients.data or []):
        end_str = pt.get("benefit_period_end")
        if not end_str:
            continue

        end_date = date.fromisoformat(end_str)
        days_left = (end_date - today).days
        name = f"{pt['first_name']} {pt['last_name']}"

        if 0 <= days_left <= 7:
            severity = "critical" if days_left <= 2 else "urgent" if days_left <= 5 else "warning"
            alerts.append(build_alert(
                agency_id, "episode_ending", severity,
                "patient", pt["id"], name,
                f"{'⛔' if days_left <= 2 else '🚨'} Episode ends in {days_left} days — {name}. "
                f"Physician order for recertification or discharge needed. "
                f"Physician: {pt.get('attending_physician_name','Unknown')}",
                str(end_date),
            ))

    return alerts


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SCANNER
# ══════════════════════════════════════════════════════════════════════════════

def run_compliance_scan(agency_id: str = None, write_to_db: bool = True) -> dict:
    """Run all compliance scans and optionally write alerts to Supabase."""
    today = date.today()

    # Load agency
    if agency_id:
        result = supabase.table("agencies").select("*").eq("id", agency_id).execute()
    else:
        result = supabase.table("agencies").select("*").execute()

    if not result.data:
        raise ValueError("No agency found")

    agency = result.data[0]
    agency_id = agency["id"]

    print(f"\n  Agency: {agency['name']}")
    print(f"  Scan date: {today.strftime('%A, %B %d, %Y')}")
    print(f"  Running {7} compliance checks...\n")

    # Run all scans
    all_alerts = []
    scan_results = {}

    scans = [
        ("NOA Filing",          scan_noa,              "noa_due"),
        ("LUPA Risk",           scan_lupa_risk,        "lupa_risk"),
        ("Credentials",         scan_credentials,      "credential_expiry"),
        ("EVV Exceptions",      scan_evv_exceptions,   "evv_exception"),
        ("Auth Exhaustion",     scan_auth_exhaustion,  "auth_exhausted"),
        ("Missed Visits",       scan_missed_visits,    "missed_visit"),
        ("Episode Endings",     scan_episode_endings,  "episode_ending"),
    ]

    for label, scan_fn, key in scans:
        alerts = scan_fn(agency_id, today)
        scan_results[key] = alerts
        all_alerts.extend(alerts)
        status = f"{len(alerts)} alerts" if alerts else "✓ Clear"
        print(f"  {'⚠️ ' if alerts else '  '}{label:25s} {status}")

    # Write to Supabase
    if write_to_db and all_alerts:
        # Clear existing unresolved alerts
        supabase.table("compliance_events")\
            .delete()\
            .eq("agency_id", agency_id)\
            .eq("is_resolved", False)\
            .execute()

        # Write new ones
        for alert in all_alerts:
            try:
                supabase.table("compliance_events").insert(alert).execute()
            except Exception as e:
                print(f"  ⚠️ Failed to write alert: {e}")

    return {
        "agency_id": agency_id,
        "agency_name": agency["name"],
        "scan_date": str(today),
        "total_alerts": len(all_alerts),
        "alerts_by_type": scan_results,
        "all_alerts": all_alerts,
    }


def print_compliance_report(result: dict):
    """Print a detailed compliance report to the terminal."""
    all_alerts = result["all_alerts"]

    critical = [a for a in all_alerts if a["severity"] == "critical"]
    urgent   = [a for a in all_alerts if a["severity"] == "urgent"]
    warning  = [a for a in all_alerts if a["severity"] == "warning"]

    print(f"\n{'═'*60}")
    print(f"  VYNDA COMPLIANCE REPORT — {result['scan_date']}")
    print(f"{'═'*60}")
    print(f"  Total alerts: {result['total_alerts']}")
    print(f"  ⛔ Critical: {len(critical)}")
    print(f"  🚨 Urgent:   {len(urgent)}")
    print(f"  ⚠️  Warning:  {len(warning)}")

    if critical:
        print(f"\n  ── CRITICAL (Immediate Action Required) ──")
        for a in critical:
            print(f"  {a['description']}")

    if urgent:
        print(f"\n  ── URGENT (Action Required Today) ──")
        for a in urgent:
            print(f"  {a['description']}")

    if warning:
        print(f"\n  ── WARNING (Action Required This Week) ──")
        for a in warning:
            print(f"  {a['description']}")

    if not all_alerts:
        print(f"\n  ✅ No compliance issues detected. Agency is fully compliant.")

    print(f"\n{'═'*60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vynda Compliance Monitor")
    parser.add_argument("--report", action="store_true", help="Print report only, don't write to DB")
    args = parser.parse_args()

    print("\n╔══════════════════════════════════════════════════╗")
    print("║     Vynda — Compliance Monitor                   ║")
    print("╚══════════════════════════════════════════════════╝")

    write = not args.report
    result = run_compliance_scan(write_to_db=write)
    print_compliance_report(result)

    if write:
        print(f"  💾 {result['total_alerts']} alerts written to Supabase\n")
