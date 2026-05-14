"""
CareOps AI — Mock Data Validation
───────────────────────────────────
Run this to confirm the mock client is working correctly
before building the scheduling engine on top of it.

Usage:
    cd backend
    python test_mock.py
"""

import asyncio
from integrations.axxess.mock import AxxessMockClient, PATIENTS, CAREGIVERS


async def run():
    client = AxxessMockClient()
    print("\n╔══════════════════════════════════════════════════╗")
    print("║     CareOps AI — Mock Data Validation            ║")
    print("╚══════════════════════════════════════════════════╝\n")

    # ── 1. Agency Overview ─────────────────────────────────────────────────
    patients = await client.search_patients()
    caregivers = await client.get_caregivers()

    print(f"📋 AGENCY OVERVIEW")
    print(f"   Total patients:   {len(patients)}")
    print(f"   Total caregivers: {len(caregivers)}")

    disc_counts = {}
    for c in caregivers:
        d = c["discipline"]
        disc_counts[d] = disc_counts.get(d, 0) + 1
    print(f"   Staff breakdown:  {disc_counts}")

    payer_counts = {}
    for p in PATIENTS:
        payer = p["detail"]["primaryPayorName"]
        payer_counts[payer] = payer_counts.get(payer, 0) + 1
    print(f"   Payer mix:        {payer_counts}")

    # ── 2. Sample Patient ──────────────────────────────────────────────────
    print(f"\n👤 SAMPLE PATIENT DETAIL")
    first_id = patients[0]["patientId"]
    detail = await client.get_patient(first_id)
    meds = await client.get_medications(first_id)
    allergies = await client.get_allergies(first_id)
    meta = await client.get_careops_patient_data(first_id)

    print(f"   Name:       {detail['firstName']} {detail['lastName']}")
    print(f"   Location:   {detail['city']}, IL")
    print(f"   GPS:        {detail['latitude']:.4f}, {detail['longitude']:.4f}")
    print(f"   Payer:      {detail['primaryPayorName']}")
    print(f"   Primary DX: {detail['diagnoses'][0]['code']} — {detail['diagnoses'][0]['description']}")
    print(f"   Diagnoses:  {len(detail['diagnoses'])} total")
    print(f"   Meds:       {len(meds)} medications")
    print(f"   Allergies:  {len(allergies)} known")
    print(f"   PDGM Group: {meta['pdgmGroup']}")
    print(f"   Visits/wk:  {meta['visitsPerWeek']}")
    print(f"   Auth status:{meta['authorizationStatus']}")
    print(f"   NOA filed:  {meta['noaFiled']}")

    # ── 3. Scheduling Data ─────────────────────────────────────────────────
    print(f"\n📅 SCHEDULING ENGINE DATA")
    all_data = await client.get_all_careops_data()
    discipline_needs = {}
    for p in all_data:
        d = p["disciplineNeeded"]
        discipline_needs[d] = discipline_needs.get(d, 0) + 1

    disc_map = {1:"RN", 2:"LPN", 3:"PT", 4:"OT", 5:"ST", 6:"HHA", 7:"MSW"}
    print("   Patient discipline needs:")
    for disc_id, count in sorted(discipline_needs.items()):
        print(f"     {disc_map.get(disc_id, disc_id):4s}: {count} patients")

    monday_rns = await client.get_available_caregivers("Monday", discipline_id=1)
    monday_pts = await client.get_available_caregivers("Monday", discipline_id=3)
    monday_hhas = await client.get_available_caregivers("Monday", discipline_id=6)
    print(f"\n   Monday availability:")
    print(f"     RNs available:  {len(monday_rns)}")
    print(f"     PTs available:  {len(monday_pts)}")
    print(f"     HHAs available: {len(monday_hhas)}")

    # ── 4. Compliance Alerts ───────────────────────────────────────────────
    print(f"\n🚨 COMPLIANCE ALERTS")
    expiring = await client.get_expiring_credentials(days_threshold=90)
    urgent = [e for e in expiring if e["isUrgent"]]
    warning = [e for e in expiring if not e["isUrgent"]]

    print(f"   Credentials expiring in 90 days: {len(expiring)}")
    print(f"   URGENT (< 30 days):              {len(urgent)}")
    if urgent:
        for u in urgent:
            print(f"     ⚠️  {u['caregiverName']} — {u['credentialType']} expires in {u['daysUntilExpiry']} days")
    print(f"   Warning (30–90 days):            {len(warning)}")
    if warning:
        for w in warning[:3]:
            print(f"     ⚡ {w['caregiverName']} — {w['credentialType']} expires in {w['daysUntilExpiry']} days")

    # ── 5. LUPA Risk ───────────────────────────────────────────────────────
    print(f"\n💰 LUPA RISK PATIENTS (Revenue at Risk)")
    lupa_risk = await client.get_lupa_risk_patients()
    high = [l for l in lupa_risk if l["riskLevel"] == "HIGH"]
    medium = [l for l in lupa_risk if l["riskLevel"] == "MEDIUM"]

    print(f"   High risk:   {len(high)} patients")
    print(f"   Medium risk: {len(medium)} patients")
    if high:
        print(f"\n   Top HIGH risk patients:")
        for h in high[:3]:
            print(f"     💸 {h['patientName']:25s} — {h['shortfall']} visits short | {h['pdgmGroup']}")

    # ── 6. Full Profile Test ───────────────────────────────────────────────
    print(f"\n🔬 FULL PATIENT PROFILE (parallel fetch)")
    profile = await client.get_full_patient_profile(first_id)
    print(f"   Patient:      {profile['patient']['firstName']} {profile['patient']['lastName']}")
    print(f"   Care plan:    {len(profile['care_plan'])} areas")
    print(f"   Medications:  {len(profile['medications'])} total")
    print(f"   Allergies:    {len(profile['allergies'])} total")
    print(f"   Pulled at:    {profile['pulled_at'][:19]}")

    print(f"\n{'═'*52}")
    print(f"✅ All mock data validated — ready to build scheduler")
    print(f"{'═'*52}\n")


if __name__ == "__main__":
    asyncio.run(run())
