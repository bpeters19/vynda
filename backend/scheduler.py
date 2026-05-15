"""
Vynda — AI Scheduling Engine
──────────────────────────────
Reads patients and caregivers from Supabase, matches them using a
multi-factor scoring algorithm, and writes an optimized daily schedule.

Matching factors (weighted scoring):
  1. Discipline match      — caregiver must have required discipline (hard filter)
  2. Geographic proximity  — minimize drive time between visits
  3. Availability          — caregiver must work that day of week
  4. Capacity              — caregiver must not exceed max patients/day
  5. Continuity            — prefer same caregiver as previous visits
  6. LUPA priority         — patients behind on visits get scheduled first
  7. Authorization status  — don't schedule without active auth

Usage:
    cd backend
    python scheduler.py              # schedule for today
    python scheduler.py 2026-05-20   # schedule for a specific date
"""

import os
import sys
import math
import asyncio
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

load_dotenv()

# ── Supabase ──────────────────────────────────────────────────────────────────
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
except Exception as e:
    print(f"❌ Supabase connection failed: {e}")
    sys.exit(1)

# ── Constants ─────────────────────────────────────────────────────────────────

DISCIPLINE_MAP = {
    1: "RN", 2: "LPN", 3: "PT", 4: "OT", 5: "ST", 6: "HHA", 7: "MSW"
}

# Scoring weights — adjust these to tune the algorithm
WEIGHTS = {
    "proximity":   40,   # closer = better (up to 40 points)
    "continuity":  25,   # same caregiver as before (25 points)
    "lupa_urgent": 20,   # patient is behind on visits (20 points)
    "capacity":    15,   # caregiver has more open slots (15 points)
}

# Visit duration estimates by discipline (minutes)
VISIT_DURATIONS = {
    "RN": 60, "LPN": 45, "PT": 60, "OT": 60,
    "ST": 45, "HHA": 120, "MSW": 60
}

# Max drive distance we'll tolerate between visits (miles)
MAX_DRIVE_MILES = 25


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate straight-line distance between two GPS coordinates in miles.
    Used for caregiver-to-patient proximity scoring.
    """
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_drive_time(miles: float) -> int:
    """Estimate drive time in minutes (assumes 25mph average in suburban IL)."""
    return int((miles / 25) * 60)


def day_of_week(d: date) -> str:
    """Return full day name for a date."""
    return d.strftime("%A")  # Monday, Tuesday, etc.


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_agency(agency_id: str = None) -> dict:
    """Load the first agency (or a specific one)."""
    if agency_id:
        result = supabase.table("agencies").select("*").eq("id", agency_id).execute()
    else:
        result = supabase.table("agencies").select("*").execute()
    if not result.data:
        raise ValueError("No agency found in database")
    return result.data[0]


def load_active_caregivers(agency_id: str) -> list[dict]:
    """Load all active caregivers for an agency."""
    result = supabase.table("caregivers")\
        .select("*")\
        .eq("agency_id", agency_id)\
        .eq("status", "active")\
        .execute()
    return result.data or []


def load_active_patients(agency_id: str) -> list[dict]:
    """Load all active patients for an agency."""
    result = supabase.table("patients")\
        .select("*")\
        .eq("agency_id", agency_id)\
        .eq("status", 1)\
        .execute()
    return result.data or []


def load_existing_schedules(agency_id: str, visit_date: date) -> list[dict]:
    """Load any schedules already created for a given date."""
    result = supabase.table("schedules")\
        .select("*")\
        .eq("agency_id", agency_id)\
        .eq("visit_date", str(visit_date))\
        .execute()
    return result.data or []


def load_recent_schedules(agency_id: str, days_back: int = 14) -> list[dict]:
    """
    Load recent completed schedules — used for continuity scoring.
    Tells us which caregiver has been seeing which patient.
    """
    since = str(date.today() - timedelta(days=days_back))
    result = supabase.table("schedules")\
        .select("patient_id, caregiver_id, discipline")\
        .eq("agency_id", agency_id)\
        .gte("visit_date", since)\
        .eq("status", "completed")\
        .execute()
    return result.data or []


# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULING LOGIC
# ══════════════════════════════════════════════════════════════════════════════

def build_continuity_map(recent_schedules: list[dict]) -> dict:
    """
    Build a map of patient_id → caregiver_id based on recent visit history.
    Used to prefer the same caregiver for continuity of care.
    """
    continuity = {}
    for s in recent_schedules:
        pid = s.get("patient_id")
        cid = s.get("caregiver_id")
        if pid and cid:
            continuity[pid] = cid  # last caregiver wins
    return continuity


def get_patients_needing_visit(
    patients: list[dict],
    visit_date: date,
    existing_schedules: list[dict],
) -> list[dict]:
    """
    Filter patients who need a visit on this date.

    Rules:
    - Patient must be active (status = 1)
    - Patient must have authorized visits remaining
    - Patient must not already have a visit scheduled today
    - Patient must need a visit based on visits_per_week frequency
    - LUPA risk patients get prioritized (sorted first)
    """
    already_scheduled = {s["patient_id"] for s in existing_schedules}
    today_dow = day_of_week(visit_date)
    needs_visit = []

    for pt in patients:
        # Skip if already scheduled today
        if pt["id"] in already_scheduled:
            continue

        # Skip if no authorization
        if pt.get("auth_status") not in ("approved", None):
            continue

        # Skip if episode ended
        benefit_end = pt.get("benefit_period_end")
        if benefit_end and date.fromisoformat(benefit_end) < visit_date:
            continue

        # Determine if this patient needs a visit today based on frequency
        visits_per_week = pt.get("visits_per_week", 3)
        needs_visit_today = should_visit_today(visits_per_week, visit_date, pt)

        if needs_visit_today:
            # Calculate LUPA risk score for prioritization
            pt["_lupa_risk"] = calculate_lupa_risk(pt, visit_date)
            needs_visit.append(pt)

    # Sort: LUPA risk patients first, then by patient name
    return sorted(needs_visit, key=lambda p: (-p["_lupa_risk"], p["last_name"]))


def should_visit_today(visits_per_week: int, visit_date: date, patient: dict) -> bool:
    """
    Determine if a patient should receive a visit on a given date
    based on their weekly frequency order.

    Frequency → Days:
    1x/week  → Wednesday
    2x/week  → Monday, Thursday
    3x/week  → Monday, Wednesday, Friday
    4x/week  → Monday, Tuesday, Thursday, Friday
    5x/week  → Monday, Tuesday, Wednesday, Thursday, Friday
    6x/week  → Monday through Saturday
    7x/week  → Every day
    """
    dow = visit_date.weekday()  # 0=Monday, 6=Sunday

    schedule_map = {
        1: [2],              # Wednesday
        2: [0, 3],           # Monday, Thursday
        3: [0, 2, 4],        # Monday, Wednesday, Friday
        4: [0, 1, 3, 4],     # Monday, Tuesday, Thursday, Friday
        5: [0, 1, 2, 3, 4],  # Monday-Friday
        6: [0, 1, 2, 3, 4, 5],  # Monday-Saturday
        7: [0, 1, 2, 3, 4, 5, 6],  # Every day
    }

    visit_days = schedule_map.get(visits_per_week, [0, 2, 4])
    return dow in visit_days


def calculate_lupa_risk(patient: dict, visit_date: date) -> float:
    """
    Calculate a LUPA risk score (0-100) for a patient.
    Higher = more urgent to get this visit in.

    LUPA = Low Utilization Payment Adjustment — if a patient doesn't
    get enough visits in a 30-day period, Medicare cuts the payment
    significantly (sometimes by 50%+).
    """
    benefit_end = patient.get("benefit_period_end")
    if not benefit_end:
        return 0

    end_date = date.fromisoformat(benefit_end)
    days_left = (end_date - visit_date).days
    visits_per_week = patient.get("visits_per_week", 3)
    visits_done = patient.get("visits_this_episode", 0)
    lupa_threshold = patient.get("lupa_threshold", 2)

    # How many visits should have happened by now
    days_into_episode = max(1, 60 - days_left)
    weeks_elapsed = days_into_episode / 7
    expected = int(visits_per_week * weeks_elapsed)
    shortfall = max(0, expected - visits_done)

    # Risk score: higher shortfall + fewer days left = more urgent
    if days_left <= 0:
        return 0  # episode over

    urgency = min(100, (shortfall / max(1, lupa_threshold)) * (30 / max(1, days_left)) * 100)
    return urgency


def score_caregiver_for_patient(
    caregiver: dict,
    patient: dict,
    continuity_map: dict,
    caregiver_load: dict,  # caregiver_id → visits already assigned today
) -> float | None:
    """
    Score a caregiver for a specific patient. Returns None if not eligible.

    Higher score = better match.
    Maximum possible score = 100.
    """
    cid = caregiver["id"]
    pid = patient["id"]

    # ── Hard filters (disqualifying) ──────────────────────────────────────────

    # 1. Discipline must match
    required_discipline_id = patient.get("discipline_needed")
    if required_discipline_id and caregiver.get("discipline_id") != required_discipline_id:
        return None

    # 2. Must be available today
    visit_date_str = day_of_week(date.today())  # passed in via context
    available_days = caregiver.get("available_days") or []
    if available_days and visit_date_str not in available_days:
        return None

    # 3. Must not exceed max patients per day
    max_load = caregiver.get("max_patients_per_day", 6)
    current_load = caregiver_load.get(cid, 0)
    if current_load >= max_load:
        return None

    # 4. Must have GPS coordinates for routing
    if not caregiver.get("latitude") or not patient.get("latitude"):
        # Can still assign but no proximity scoring
        proximity_score = 0
    else:
        # ── Scoring ───────────────────────────────────────────────────────────

        # Proximity score (0-40 points) — closer is better
        miles = haversine_miles(
            caregiver["latitude"], caregiver["longitude"],
            patient["latitude"], patient["longitude"]
        )
        if miles > MAX_DRIVE_MILES:
            return None  # too far
        proximity_score = WEIGHTS["proximity"] * max(0, 1 - (miles / MAX_DRIVE_MILES))

    # Continuity score (0-25 points) — same caregiver as last visit
    continuity_score = WEIGHTS["continuity"] if continuity_map.get(pid) == cid else 0

    # LUPA urgency score (0-20 points)
    lupa_score = WEIGHTS["lupa_urgent"] * min(1.0, patient.get("_lupa_risk", 0) / 100)

    # Capacity score (0-15 points) — prefer caregiver with more open slots
    slots_remaining = max_load - current_load
    capacity_score = WEIGHTS["capacity"] * (slots_remaining / max_load)

    total = proximity_score + continuity_score + lupa_score + capacity_score
    return round(total, 2)


def assign_visit_times(
    assignments: list[dict],
    caregiver: dict,
) -> list[dict]:
    """
    Calculate start/end times for a caregiver's visits for the day.
    Sequences visits geographically to minimize total drive time.
    """
    if not assignments:
        return assignments

    shift_start = caregiver.get("shift_start", "08:00")
    hour, minute = map(int, shift_start.split(":")[:2])
    current_time = datetime(2000, 1, 1, hour, minute)  # date doesn't matter here

    # Sort assignments by geographic proximity (nearest neighbor)
    ordered = []
    remaining = assignments.copy()
    current_lat = caregiver.get("latitude", 41.6)
    current_lng = caregiver.get("longitude", -87.7)

    while remaining:
        # Find nearest unvisited patient
        nearest = min(
            remaining,
            key=lambda a: haversine_miles(
                current_lat, current_lng,
                a["patient"].get("latitude", current_lat),
                a["patient"].get("longitude", current_lng),
            ) if a["patient"].get("latitude") else 999
        )
        ordered.append(nearest)
        remaining.remove(nearest)
        current_lat = nearest["patient"].get("latitude", current_lat)
        current_lng = nearest["patient"].get("longitude", current_lng)

    # Assign times sequentially
    discipline = caregiver.get("discipline", "RN")
    visit_duration = VISIT_DURATIONS.get(discipline, 60)

    for i, assignment in enumerate(ordered):
        # Add drive time from previous stop
        if i > 0:
            prev = ordered[i-1]["patient"]
            curr = assignment["patient"]
            if prev.get("latitude") and curr.get("latitude"):
                miles = haversine_miles(
                    prev["latitude"], prev["longitude"],
                    curr["latitude"], curr["longitude"]
                )
                drive_minutes = estimate_drive_time(miles)
                assignment["drive_time_minutes"] = drive_minutes
                assignment["distance_miles"] = round(miles, 2)
            else:
                drive_minutes = 20  # default
                assignment["drive_time_minutes"] = drive_minutes
                assignment["distance_miles"] = None
            current_time += timedelta(minutes=drive_minutes)
        else:
            assignment["drive_time_minutes"] = 0
            assignment["distance_miles"] = 0

        assignment["scheduled_start"] = current_time.strftime("%H:%M")
        current_time += timedelta(minutes=visit_duration)
        assignment["scheduled_end"] = current_time.strftime("%H:%M")
        current_time += timedelta(minutes=10)  # 10-min buffer between visits

    return ordered


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SCHEDULING FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def run_scheduler(visit_date: date, agency_id: str = None) -> dict:
    """
    Generate a full day's schedule for all patients who need a visit.

    Returns a summary dict with:
    - scheduled: list of visit assignments
    - unscheduled: patients who couldn't be matched
    - stats: summary metrics
    """
    dow = day_of_week(visit_date)
    print(f"\n  Scheduling for: {visit_date.strftime('%A, %B %d, %Y')}")

    # ── Load data ─────────────────────────────────────────────────────────────
    agency = load_agency(agency_id)
    agency_id = agency["id"]
    print(f"  Agency: {agency['name']}")

    caregivers = load_active_caregivers(agency_id)
    patients = load_active_patients(agency_id)
    existing = load_existing_schedules(agency_id, visit_date)
    recent = load_recent_schedules(agency_id)

    print(f"  Caregivers available: {len([c for c in caregivers if dow in (c.get('available_days') or [])])}/{len(caregivers)}")
    print(f"  Active patients: {len(patients)}")

    # ── Build context ─────────────────────────────────────────────────────────
    continuity_map = build_continuity_map(recent)
    caregiver_load = {}  # caregiver_id → visits assigned so far today

    # ── Get patients needing visits today ─────────────────────────────────────
    needs_visit = get_patients_needing_visit(patients, visit_date, existing)
    print(f"  Patients needing visit today: {len(needs_visit)}")

    # ── Score and match ───────────────────────────────────────────────────────
    scheduled = []
    unscheduled = []
    caregiver_assignments = {}  # caregiver_id → list of assignments

    # Override day check with actual visit date
    for c in caregivers:
        c["_available_today"] = dow in (c.get("available_days") or [])

    available_caregivers = [c for c in caregivers if c["_available_today"]]

    for patient in needs_visit:
        best_caregiver = None
        best_score = -1

        for caregiver in available_caregivers:
            score = score_caregiver_for_patient(
                caregiver, patient, continuity_map, caregiver_load
            )
            if score is not None and score > best_score:
                best_score = score
                best_caregiver = caregiver

        if best_caregiver:
            cid = best_caregiver["id"]
            caregiver_load[cid] = caregiver_load.get(cid, 0) + 1

            assignment = {
                "patient": patient,
                "caregiver": best_caregiver,
                "score": best_score,
                "is_continuity": continuity_map.get(patient["id"]) == cid,
                "lupa_risk": round(patient.get("_lupa_risk", 0), 1),
            }

            if cid not in caregiver_assignments:
                caregiver_assignments[cid] = []
            caregiver_assignments[cid].append(assignment)
            scheduled.append(assignment)
        else:
            unscheduled.append(patient)

    # ── Assign visit times per caregiver route ────────────────────────────────
    all_timed = []
    for cid, assignments in caregiver_assignments.items():
        caregiver = next(c for c in caregivers if c["id"] == cid)
        timed = assign_visit_times(assignments, caregiver)
        all_timed.extend(timed)

    return {
        "visit_date": str(visit_date),
        "agency_id": agency_id,
        "scheduled": all_timed,
        "unscheduled": unscheduled,
        "caregiver_assignments": caregiver_assignments,
        "stats": {
            "total_patients_needing_visit": len(needs_visit),
            "total_scheduled": len(all_timed),
            "total_unscheduled": len(unscheduled),
            "caregivers_utilized": len(caregiver_assignments),
            "caregivers_available": len(available_caregivers),
            "coverage_rate": round(len(all_timed) / max(1, len(needs_visit)) * 100, 1),
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# WRITE TO SUPABASE
# ══════════════════════════════════════════════════════════════════════════════

def save_schedule_to_supabase(schedule_result: dict) -> int:
    """Write all scheduled visits to the schedules table."""
    visit_date = schedule_result["visit_date"]
    agency_id = schedule_result["agency_id"]
    rows_inserted = 0

    for assignment in schedule_result["scheduled"]:
        patient = assignment["patient"]
        caregiver = assignment["caregiver"]

        row = {
            "agency_id":           agency_id,
            "patient_id":          patient["id"],
            "caregiver_id":        caregiver["id"],
            "visit_date":          visit_date,
            "scheduled_start":     assignment.get("scheduled_start"),
            "scheduled_end":       assignment.get("scheduled_end"),
            "discipline":          caregiver.get("discipline", "RN"),
            "visit_type":          "routine",
            "status":              "scheduled",
            "assigned_by":         "ai",
            "distance_miles":      assignment.get("distance_miles"),
            "drive_time_minutes":  assignment.get("drive_time_minutes"),
            "notes": (
                f"AI assigned. Score: {assignment['score']}. "
                f"{'Continuity visit. ' if assignment['is_continuity'] else ''}"
                f"{'⚠️ LUPA risk: ' + str(assignment['lupa_risk']) if assignment['lupa_risk'] > 30 else ''}"
            ).strip(),
        }

        supabase.table("schedules").insert(row).execute()
        rows_inserted += 1

    return rows_inserted


# ══════════════════════════════════════════════════════════════════════════════
# PRINT SCHEDULE
# ══════════════════════════════════════════════════════════════════════════════

def print_schedule(schedule_result: dict):
    """Print a formatted daily schedule to the terminal."""
    stats = schedule_result["stats"]
    visit_date = schedule_result["visit_date"]

    print(f"\n{'═'*60}")
    print(f"  VYNDA DAILY SCHEDULE — {visit_date}")
    print(f"{'═'*60}")
    print(f"  Coverage: {stats['total_scheduled']}/{stats['total_patients_needing_visit']} patients ({stats['coverage_rate']}%)")
    print(f"  Caregivers utilized: {stats['caregivers_utilized']}/{stats['caregivers_available']} available")

    # Group by caregiver
    by_caregiver = {}
    for a in schedule_result["scheduled"]:
        cname = f"{a['caregiver']['first_name']} {a['caregiver']['last_name']}"
        disc = a['caregiver']['discipline']
        key = f"{cname} ({disc})"
        if key not in by_caregiver:
            by_caregiver[key] = []
        by_caregiver[key].append(a)

    for caregiver_name, visits in sorted(by_caregiver.items()):
        print(f"\n  👤 {caregiver_name} — {len(visits)} visits")
        for v in visits:
            pt = v["patient"]
            start = v.get("scheduled_start", "TBD")
            end = v.get("scheduled_end", "TBD")
            miles = v.get("distance_miles", 0)
            lupa = f" ⚠️ LUPA" if v["lupa_risk"] > 30 else ""
            continuity = " ✓" if v["is_continuity"] else ""
            print(
                f"     {start}–{end}  "
                f"{pt['first_name']} {pt['last_name']:20s} "
                f"{pt.get('city',''):15s} "
                f"{miles:.1f}mi{continuity}{lupa}"
            )

    if schedule_result["unscheduled"]:
        print(f"\n  ⚠️  UNSCHEDULED ({len(schedule_result['unscheduled'])} patients):")
        for pt in schedule_result["unscheduled"]:
            disc_id = pt.get("discipline_needed")
            disc = DISCIPLINE_MAP.get(disc_id, "Unknown")
            print(f"     {pt['first_name']} {pt['last_name']:20s} needs {disc} — no caregiver available")

    print(f"\n{'═'*60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Parse date argument or use today
    if len(sys.argv) > 1:
        try:
            visit_date = date.fromisoformat(sys.argv[1])
        except ValueError:
            print(f"❌ Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        visit_date = date.today()

    print("\n╔══════════════════════════════════════════════════╗")
    print("║     Vynda — AI Scheduling Engine                 ║")
    print("╚══════════════════════════════════════════════════╝")

    # Run scheduler
    result = run_scheduler(visit_date)

    # Print to terminal
    print_schedule(result)

    # Save to Supabase
    if result["scheduled"]:
        print("  💾 Saving schedule to Supabase...")
        saved = save_schedule_to_supabase(result)
        print(f"  ✅ {saved} visits saved to database\n")
    else:
        print("  ℹ️  No visits to schedule for this date\n")
