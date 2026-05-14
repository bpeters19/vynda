"""
Axxess API Connection Test
──────────────────────────
Run this script once you have your Axxess API credentials to validate
the connection is working before building on top of it.

Usage:
    cd backend
    cp .env.example .env
    # fill in your real credentials in .env
    python test_axxess.py
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from integrations.axxess.client import AxxessClient, AxxessAPIError, AxxessAuthError


async def run_tests():
    print("\n🔌 CareOps AI — Axxess API Connection Test")
    print("=" * 50)

    client = AxxessClient()

    # ── Test 1: Authentication ──────────────────────────────
    print("\n[1/4] Testing authentication...")
    try:
        token = await client._fetch_token()
        print(f"  ✅ Auth successful — token received ({len(token)} chars)")
    except AxxessAuthError as e:
        print(f"  ❌ Auth FAILED: {e}")
        print("  → Check AXXESS_CLIENT_ID, AXXESS_CLIENT_SECRET, AXXESS_AUTH_URL")
        return

    # ── Test 2: Patient Search ──────────────────────────────
    print("\n[2/4] Testing patient search...")
    try:
        # Search with no filters — returns first page of all patients
        results = await client.search_patients()
        if isinstance(results, list) and len(results) > 0:
            first = results[0]
            print(f"  ✅ Found {len(results)} patients")
            print(f"  → First patient: {first.get('firstName')} {first.get('lastName')}")
            test_patient_id = first.get("patientId")
        else:
            print("  ⚠️  No patients returned — agency may have no active patients")
            test_patient_id = None
    except AxxessAPIError as e:
        print(f"  ❌ Patient search FAILED: {e}")
        test_patient_id = None

    # ── Test 3: Patient Detail ──────────────────────────────
    if test_patient_id:
        print(f"\n[3/4] Testing patient detail fetch (ID: {test_patient_id})...")
        try:
            patient = await client.get_patient(test_patient_id)
            print(f"  ✅ Patient detail received")
            print(f"  → Name: {patient.get('firstName')} {patient.get('lastName')}")
            print(f"  → DOB: {patient.get('dateOfBirth', 'N/A')}")
            print(f"  → Payer: {patient.get('primaryPayorName', 'N/A')}")
            diagnoses = patient.get("diagnoses", [])
            print(f"  → Diagnoses: {len(diagnoses)} ICD-10 codes")
            if diagnoses:
                primary = next((d for d in diagnoses if d.get("order") == 0), diagnoses[0])
                print(f"  → Primary DX: {primary.get('code')} — {primary.get('description')}")
            has_coords = patient.get("latitude") and patient.get("longitude")
            print(f"  → GPS coordinates: {'✅ Yes' if has_coords else '⚠️  Missing (needed for scheduling)'}")
        except AxxessAPIError as e:
            print(f"  ❌ Patient detail FAILED: {e}")
    else:
        print("\n[3/4] Skipping patient detail test — no patient ID available")

    # ── Test 4: Care Plan ───────────────────────────────────
    if test_patient_id:
        print(f"\n[4/4] Testing care plan fetch...")
        try:
            care_plan = await client.get_care_plan(test_patient_id)
            print(f"  ✅ Care plan received — {len(care_plan)} care areas")
            for area in care_plan[:2]:  # show first 2
                print(f"  → Area: {area.get('name')} ({len(area.get('statements', []))} statements)")
        except AxxessAPIError as e:
            print(f"  ❌ Care plan FAILED: {e}")
    else:
        print("\n[4/4] Skipping care plan test — no patient ID available")

    # ── Summary ─────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("✅ Axxess connection test complete")
    print("→ Next step: build the scheduling engine on top of this")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
