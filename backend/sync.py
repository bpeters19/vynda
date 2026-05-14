"""
Vynda — Supabase Sync Layer
────────────────────────────
Reads from the Axxess mock client (or real client when credentials arrive)
and writes everything into the live Supabase database.

Usage:
    cd backend
    python sync.py

This will:
1. Find the pilot agency in Supabase
2. Sync all 50 mock patients
3. Sync all 15 mock caregivers + their credentials
4. Generate compliance events for any issues found
5. Print a summary of everything written

Swap AxxessMockClient → AxxessClient when real credentials arrive.
"""

import asyncio
import os
import sys
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

# ── Supabase client setup ──────────────────────────────────────────────────────
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
except ImportError:
    print("❌ supabase package not installed. Run: pip install supabase")
    sys.exit(1)

# ── Mock client (swap for real AxxessClient when credentials arrive) ──────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from integrations.axxess.mock import AxxessMockClient, PATIENTS, CAREGIVERS

client = AxxessMockClient()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def parse_date(val) -> str | None:
    """Convert ISO datetime string to date string for Supabase."""
    if not val:
        return None
    try:
        if isinstance(val, str):
            return val[:10]  # take just YYYY-MM-DD
        if isinstance(val, (datetime, date)):
            return str(val)[:10]
    except Exception:
        pass
    return None


def parse_time(val) -> str | None:
    """Convert HH:MM string to time for Supabase."""
    if not val:
        return None
    return val if ":" in val else None


# ══════════════════════════════════════════════════════════════════════════════
# SYNC FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_agency_id() -> str:
    """Get the pilot agency ID from Supabase."""
    result = supabase.table("agencies").select("id, name").execute()
    if not result.data:
        raise ValueError("No agency found in database. Did you run schema.sql?")
    agency = result.data[0]
    print(f"  → Agency: {agency['name']} ({agency['id'][:8]}...)")
    return agency["id"]


def sync_caregivers(agency_id: str) -> dict:
    """
    Sync all 15 caregivers into Supabase.
    Returns a mapping of mock caregiver ID → Supabase caregiver ID.
    """
    print(f"\n👥 Syncing {len(CAREGIVERS)} caregivers...")
    id_map = {}
    inserted = 0
    updated = 0

    for c in CAREGIVERS:
        row = {
            "agency_id":            agency_id,
            "first_name":           c["firstName"],
            "last_name":            c["lastName"],
            "discipline":           c["discipline"],
            "discipline_id":        c["disciplineId"],
            "license_number":       c.get("licenseNumber"),
            "license_expiry":       parse_date(c.get("licenseExpiry")),
            "phone":                c.get("phone"),
            "email":                c.get("email"),
            "address_line1":        c.get("address"),
            "latitude":             c.get("latitude"),
            "longitude":            c.get("longitude"),
            "max_patients_per_day": c.get("maxPatientsPerDay", 6),
            "available_days":       c.get("availableDays", []),
            "shift_start":          parse_time(c.get("shiftStart")),
            "shift_end":            parse_time(c.get("shiftEnd")),
            "skills":               c.get("skills", []),
            "years_experience":     c.get("yearsExperience"),
            "is_on_call":           c.get("isOnCall", False),
            "status":               c.get("status", "active"),
            "cpx_expiry":           parse_date(c.get("cpxExpiry")),
            "tb_test_expiry":       parse_date(c.get("tbTestExpiry")),
        }

        # Upsert based on email (unique per agency)
        existing = supabase.table("caregivers")\
            .select("id")\
            .eq("agency_id", agency_id)\
            .eq("email", c["email"])\
            .execute()

        if existing.data:
            caregiver_id = existing.data[0]["id"]
            supabase.table("caregivers").update(row).eq("id", caregiver_id).execute()
            updated += 1
        else:
            result = supabase.table("caregivers").insert(row).execute()
            caregiver_id = result.data[0]["id"]
            inserted += 1

        id_map[c["id"]] = caregiver_id

        # Sync credentials
        sync_caregiver_credentials(caregiver_id, c)

    print(f"  → Inserted: {inserted} | Updated: {updated}")
    return id_map


def sync_caregiver_credentials(caregiver_id: str, c: dict):
    """Write license, CPR, and TB test credentials for a caregiver."""
    credentials = [
        {
            "caregiver_id":    caregiver_id,
            "credential_type": "license",
            "credential_number": c.get("licenseNumber"),
            "expiry_date":     parse_date(c.get("licenseExpiry")),
            "is_active":       True,
        },
        {
            "caregiver_id":    caregiver_id,
            "credential_type": "cpr",
            "expiry_date":     parse_date(c.get("cpxExpiry")),
            "is_active":       True,
        },
        {
            "caregiver_id":    caregiver_id,
            "credential_type": "tb_test",
            "expiry_date":     parse_date(c.get("tbTestExpiry")),
            "is_active":       True,
        },
    ]

    for cred in credentials:
        if not cred.get("expiry_date"):
            continue
        # Check if already exists
        existing = supabase.table("caregiver_credentials")\
            .select("id")\
            .eq("caregiver_id", caregiver_id)\
            .eq("credential_type", cred["credential_type"])\
            .execute()

        if existing.data:
            supabase.table("caregiver_credentials")\
                .update(cred)\
                .eq("id", existing.data[0]["id"])\
                .execute()
        else:
            supabase.table("caregiver_credentials").insert(cred).execute()


def sync_patients(agency_id: str) -> dict:
    """
    Sync all 50 patients into Supabase.
    Returns a mapping of Axxess patient ID → Supabase patient ID.
    """
    print(f"\n🏥 Syncing {len(PATIENTS)} patients...")
    id_map = {}
    inserted = 0
    updated = 0

    for p in PATIENTS:
        detail = p["detail"]
        meta = p["_careops"]
        diagnoses = detail.get("diagnoses", [])
        primary_dx = next((d for d in diagnoses if d.get("order") == 0), None)
        all_codes = [d["code"] for d in diagnoses if d.get("code")]

        row = {
            "agency_id":                agency_id,
            "axxess_patient_id":        detail["id"],
            "axxess_admission_id":      detail.get("latestAdmissionId"),
            "first_name":               detail["firstName"],
            "last_name":                detail["lastName"],
            "date_of_birth":            parse_date(detail.get("dateOfBirth")),
            "gender":                   detail.get("gender"),
            "medical_record_number":    detail.get("medicalRecordNumber"),
            "address_line1":            detail.get("addressLine1"),
            "city":                     detail.get("city"),
            "state":                    detail.get("state"),
            "zip_code":                 detail.get("zipCode"),
            "latitude":                 detail.get("latitude"),
            "longitude":                detail.get("longitude"),
            "preferred_phone":          detail.get("preferredPhone"),
            "primary_payor_name":       detail.get("primaryPayorName"),
            "medicare_number":          detail.get("medicareNumber"),
            "medicare_beneficiary_id":  detail.get("medicareBeneficiaryIdentification"),
            "medicaid_number":          detail.get("medicaidNumber"),
            "admission_date":           parse_date(detail.get("admissionDate")),
            "benefit_period_start":     parse_date(detail.get("benefitPeriodStartDate")),
            "benefit_period_end":       parse_date(detail.get("benefitPeriodEndDate")),
            "is_transfer":              detail.get("isTransfer", False),
            "is_re_admit":              detail.get("isReAdmit", False),
            "attending_physician_name": detail.get("attendingPhysicianName"),
            "level_of_care":            detail.get("levelOfCare"),
            "line_of_service":          detail.get("lineOfService"),
            "is_dnr":                   detail.get("isDoNotResuscitate", False),
            "is_hospitalized":          detail.get("isHospitalized", False),
            "status":                   detail.get("status", 1),
            "pdgm_group":               meta.get("pdgmGroup"),
            "primary_icd10":            primary_dx["code"] if primary_dx else None,
            "all_icd10_codes":          all_codes,
            "auth_status":              meta.get("authorizationStatus", "approved"),
            "auth_visits_approved":     meta.get("authVisitsApproved"),
            "noa_filed":                meta.get("noaFiled", False),
            "noa_date":                 parse_date(meta.get("noaDate")),
            "visits_per_week":          meta.get("visitsPerWeek", 3),
            "visits_this_episode":      meta.get("visitsThisEpisode", 0),
            "lupa_threshold":           meta.get("lupaThreshold", 2),
            "discipline_needed":        meta.get("disciplineNeeded"),
            "last_synced_at":           datetime.now().isoformat(),
        }

        # Upsert on Axxess patient ID
        existing = supabase.table("patients")\
            .select("id")\
            .eq("axxess_patient_id", detail["id"])\
            .execute()

        if existing.data:
            patient_id = existing.data[0]["id"]
            supabase.table("patients").update(row).eq("id", patient_id).execute()
            updated += 1
        else:
            result = supabase.table("patients").insert(row).execute()
            patient_id = result.data[0]["id"]
            inserted += 1

        id_map[detail["id"]] = patient_id

        # Sync diagnoses, medications, allergies
        sync_patient_diagnoses(patient_id, diagnoses)
        sync_patient_medications(patient_id, p["medications"])
        sync_patient_allergies(patient_id, p["allergies"])

    print(f"  → Inserted: {inserted} | Updated: {updated}")
    return id_map


def sync_patient_diagnoses(patient_id: str, diagnoses: list):
    """Write ICD-10 diagnoses for a patient."""
    # Clear and rewrite — diagnoses change
    supabase.table("patient_diagnoses")\
        .delete()\
        .eq("patient_id", patient_id)\
        .execute()

    for dx in diagnoses:
        supabase.table("patient_diagnoses").insert({
            "patient_id":   patient_id,
            "icd10_code":   dx.get("code", ""),
            "description":  dx.get("description"),
            "dx_order":     dx.get("order", 0),
            "is_related":   dx.get("isRelated", True),
            "start_date":   parse_date(dx.get("startDate")),
            "resolved_date": parse_date(dx.get("resolvedDate")),
        }).execute()


def sync_patient_medications(patient_id: str, medications: list):
    """Write medications for a patient."""
    supabase.table("patient_medications")\
        .delete()\
        .eq("patient_id", patient_id)\
        .execute()

    for med in medications:
        supabase.table("patient_medications").insert({
            "patient_id":         patient_id,
            "medication_name":    med.get("medicationName", ""),
            "dosage":             med.get("dosage"),
            "route":              med.get("route"),
            "frequency":          med.get("frequency"),
            "classification":     med.get("classification"),
            "is_prn":             med.get("isPrn", False),
            "start_date":         parse_date(med.get("startDate")),
            "discontinue_date":   parse_date(med.get("discontinueDate")),
            "is_active":          med.get("discontinueDate") is None,
            "added_by_physician": med.get("addedByPhysician"),
        }).execute()


def sync_patient_allergies(patient_id: str, allergies: list):
    """Write allergies for a patient."""
    supabase.table("patient_allergies")\
        .delete()\
        .eq("patient_id", patient_id)\
        .execute()

    for al in allergies:
        supabase.table("patient_allergies").insert({
            "patient_id": patient_id,
            "allergy":    al.get("allergy", ""),
            "reaction":   al.get("reaction"),
            "severity":   al.get("severity"),
            "is_active":  al.get("endDate") is None,
            "start_date": parse_date(al.get("startDate")),
            "end_date":   parse_date(al.get("endDate")),
        }).execute()


def generate_compliance_events(agency_id: str):
    """
    Scan for compliance issues and write them to the compliance_events table.
    This is what the compliance monitor dashboard reads from.
    """
    print(f"\n🚨 Generating compliance events...")
    events_written = 0

    # Clear existing unresolved events before regenerating
    supabase.table("compliance_events")\
        .delete()\
        .eq("agency_id", agency_id)\
        .eq("is_resolved", False)\
        .execute()

    today = datetime.now().date()

    # ── Credential expiry alerts ──────────────────────────────────────────────
    creds = supabase.table("caregiver_credentials")\
        .select("*, caregivers(first_name, last_name, discipline)")\
        .eq("is_active", True)\
        .execute()

    for cred in creds.data:
        expiry = date.fromisoformat(cred["expiry_date"])
        days_left = (expiry - today).days
        caregiver = cred.get("caregivers", {})
        name = f"{caregiver.get('first_name','')} {caregiver.get('last_name','')}".strip()

        if days_left <= 90:
            severity = "critical" if days_left <= 0 else \
                       "urgent" if days_left <= 30 else "warning"

            label = "EXPIRED" if days_left <= 0 else f"expires in {days_left} days"

            supabase.table("compliance_events").insert({
                "agency_id":   agency_id,
                "event_type":  "credential_expiry",
                "severity":    severity,
                "entity_type": "caregiver",
                "entity_id":   cred["caregiver_id"],
                "entity_name": name,
                "description": f"{name} ({caregiver.get('discipline','')}) — {cred['credential_type'].replace('_',' ').title()} {label}",
                "due_date":    cred["expiry_date"],
                "is_resolved": False,
            }).execute()
            events_written += 1

    # ── LUPA risk alerts ──────────────────────────────────────────────────────
    patients = supabase.table("patients")\
        .select("id, first_name, last_name, visits_per_week, visits_this_episode, lupa_threshold, benefit_period_end, pdgm_group")\
        .eq("agency_id", agency_id)\
        .eq("status", 1)\
        .execute()

    for pt in patients.data:
        benefit_end = pt.get("benefit_period_end")
        if not benefit_end:
            continue

        end_date = date.fromisoformat(benefit_end)
        days_left_in_episode = (end_date - today).days
        weeks_elapsed = max(1, (60 - days_left_in_episode) // 7)
        expected = pt["visits_per_week"] * weeks_elapsed
        actual = pt["visits_this_episode"] or 0
        shortfall = expected - actual

        if shortfall >= pt["lupa_threshold"]:
            name = f"{pt['first_name']} {pt['last_name']}"
            supabase.table("compliance_events").insert({
                "agency_id":   agency_id,
                "event_type":  "lupa_risk",
                "severity":    "urgent" if shortfall >= pt["lupa_threshold"] * 2 else "warning",
                "entity_type": "patient",
                "entity_id":   pt["id"],
                "entity_name": name,
                "description": f"{name} — {shortfall} visits behind pace. Risk of LUPA payment reduction. ({pt.get('pdgm_group','')})",
                "due_date":    benefit_end,
                "is_resolved": False,
            }).execute()
            events_written += 1

    # ── NOA due alerts ────────────────────────────────────────────────────────
    for pt in patients.data:
        admission = supabase.table("patients")\
            .select("admission_date, noa_filed, noa_due_date, first_name, last_name")\
            .eq("id", pt["id"])\
            .execute()

        if not admission.data:
            continue

        p = admission.data[0]
        if p["noa_filed"]:
            continue

        admission_date = p.get("admission_date")
        if not admission_date:
            continue

        noa_due = date.fromisoformat(admission_date) + __import__('datetime').timedelta(days=5)
        days_until_due = (noa_due - today).days
        name = f"{p['first_name']} {p['last_name']}"

        if days_until_due <= 5:
            supabase.table("compliance_events").insert({
                "agency_id":   agency_id,
                "event_type":  "noa_due",
                "severity":    "critical" if days_until_due <= 1 else "urgent",
                "entity_type": "patient",
                "entity_id":   pt["id"],
                "entity_name": name,
                "description": f"{name} — NOA not filed. Due {noa_due.strftime('%b %d')} ({days_until_due} days). Late filing = claim denial.",
                "due_date":    str(noa_due),
                "is_resolved": False,
            }).execute()
            events_written += 1

    print(f"  → {events_written} compliance events written")


async def run_sync():
    print("\n╔══════════════════════════════════════════════════╗")
    print("║     Vynda — Supabase Sync                        ║")
    print("╚══════════════════════════════════════════════════╝\n")

    print("🔌 Connecting to Supabase...")
    agency_id = get_agency_id()

    caregiver_id_map = sync_caregivers(agency_id)
    patient_id_map = sync_patients(agency_id)
    generate_compliance_events(agency_id)

    # ── Summary ───────────────────────────────────────────────────────────────
    caregivers_count = supabase.table("caregivers").select("id", count="exact").eq("agency_id", agency_id).execute()
    patients_count = supabase.table("patients").select("id", count="exact").eq("agency_id", agency_id).execute()
    events_count = supabase.table("compliance_events").select("id", count="exact").eq("agency_id", agency_id).execute()
    creds_count = supabase.table("caregiver_credentials").select("id", count="exact").execute()

    print(f"\n{'═'*52}")
    print(f"✅ Sync complete")
    print(f"   Caregivers in Supabase:    {caregivers_count.count}")
    print(f"   Patients in Supabase:      {patients_count.count}")
    print(f"   Credentials tracked:       {creds_count.count}")
    print(f"   Compliance events active:  {events_count.count}")
    print(f"{'═'*52}")
    print(f"\n→ Next step: open Supabase Table Editor and verify the data")
    print(f"→ Then: build the scheduling engine\n")


if __name__ == "__main__":
    asyncio.run(run_sync())
