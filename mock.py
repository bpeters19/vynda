"""
CareOps AI — Mock Axxess Data
──────────────────────────────
Realistic mock data that exactly mirrors the Axxess API response shapes.
50 patients, 15 caregivers, visits, authorizations, and schedules.

Used for:
- Building and testing the scheduling engine without live credentials
- Frontend dashboard development
- Unit testing all modules

Swap out by replacing AxxessMockClient with AxxessClient when credentials arrive.
"""

from datetime import datetime, timedelta
from uuid import uuid4
import random

# ── Helpers ────────────────────────────────────────────────────────────────

def uid(): return str(uuid4())
def days_ago(n): return (datetime.now() - timedelta(days=n)).isoformat() + "Z"
def days_from_now(n): return (datetime.now() + timedelta(days=n)).isoformat() + "Z"
def today(): return datetime.now().isoformat() + "Z"

# ── Chicago Area Coordinates (real neighborhoods) ─────────────────────────

CHICAGO_LOCATIONS = [
    {"neighborhood": "Oak Forest",       "lat": 41.6197, "lng": -87.7478},
    {"neighborhood": "Tinley Park",      "lat": 41.5731, "lng": -87.7873},
    {"neighborhood": "Orland Park",      "lat": 41.6031, "lng": -87.8540},
    {"neighborhood": "Matteson",         "lat": 41.5050, "lng": -87.7145},
    {"neighborhood": "Harvey",           "lat": 41.6100, "lng": -87.6467},
    {"neighborhood": "Calumet City",     "lat": 41.6153, "lng": -87.5298},
    {"neighborhood": "Lansing",          "lat": 41.5642, "lng": -87.5381},
    {"neighborhood": "Dolton",           "lat": 41.6267, "lng": -87.6087},
    {"neighborhood": "Chicago Heights",  "lat": 41.5061, "lng": -87.6356},
    {"neighborhood": "Homewood",         "lat": 41.5592, "lng": -87.6612},
    {"neighborhood": "Flossmoor",        "lat": 41.5381, "lng": -87.6823},
    {"neighborhood": "Park Forest",      "lat": 41.4831, "lng": -87.6740},
    {"neighborhood": "Richton Park",     "lat": 41.4831, "lng": -87.7373},
    {"neighborhood": "Olympia Fields",   "lat": 41.5131, "lng": -87.6901},
    {"neighborhood": "Frankfort",        "lat": 41.4964, "lng": -87.8512},
]

# ── ICD-10 Codes (most common in home health under PDGM) ──────────────────

COMMON_DIAGNOSES = [
    {"code": "I50.9",  "description": "Heart failure, unspecified",              "pdgm_group": "MMTA - Cardiac"},
    {"code": "I10",    "description": "Essential (primary) hypertension",        "pdgm_group": "MMTA - Cardiac"},
    {"code": "E11.9",  "description": "Type 2 diabetes mellitus without complications", "pdgm_group": "MMTA - Endocrine"},
    {"code": "M17.11", "description": "Primary osteoarthritis, right knee",      "pdgm_group": "Musculoskeletal Rehabilitation"},
    {"code": "I69.351","description": "Hemiplegia following cerebral infarction","pdgm_group": "Neuro/Stroke Rehabilitation"},
    {"code": "J44.1",  "description": "COPD with acute exacerbation",            "pdgm_group": "MMTA - Respiratory"},
    {"code": "L89.310","description": "Pressure ulcer of right buttock",         "pdgm_group": "Wounds"},
    {"code": "M54.5",  "description": "Low back pain",                           "pdgm_group": "Musculoskeletal Rehabilitation"},
    {"code": "G30.9",  "description": "Alzheimer's disease, unspecified",        "pdgm_group": "Behavioral Health"},
    {"code": "N39.0",  "description": "Urinary tract infection",                 "pdgm_group": "MMTA - Infectious Disease"},
    {"code": "Z96.641","description": "Presence of right artificial hip joint",  "pdgm_group": "Musculoskeletal Rehabilitation"},
    {"code": "I63.9",  "description": "Cerebral infarction, unspecified",        "pdgm_group": "Neuro/Stroke Rehabilitation"},
    {"code": "E11.65", "description": "Type 2 diabetes with hyperglycemia",      "pdgm_group": "MMTA - Endocrine"},
    {"code": "M16.11", "description": "Primary osteoarthritis, right hip",       "pdgm_group": "Musculoskeletal Rehabilitation"},
    {"code": "I48.91", "description": "Unspecified atrial fibrillation",         "pdgm_group": "MMTA - Cardiac"},
]

COMORBIDITIES = [
    {"code": "I10",    "description": "Essential hypertension"},
    {"code": "E11.9",  "description": "Type 2 diabetes"},
    {"code": "E78.5",  "description": "Hyperlipidemia"},
    {"code": "F32.9",  "description": "Major depressive disorder"},
    {"code": "N18.3",  "description": "Chronic kidney disease, stage 3"},
    {"code": "J45.909","description": "Unspecified asthma"},
    {"code": "M79.3",  "description": "Panniculitis"},
    {"code": "Z87.891","description": "Personal history of nicotine dependence"},
]

# ── Common Medications ─────────────────────────────────────────────────────

MEDICATIONS_POOL = [
    {"name": "Metoprolol Succinate 50mg",  "route": "Oral", "frequency": "Daily",    "classification": "Beta Blocker"},
    {"name": "Lisinopril 10mg",            "route": "Oral", "frequency": "Daily",    "classification": "ACE Inhibitor"},
    {"name": "Furosemide 40mg",            "route": "Oral", "frequency": "BID",      "classification": "Loop Diuretic"},
    {"name": "Metformin 500mg",            "route": "Oral", "frequency": "BID",      "classification": "Antidiabetic"},
    {"name": "Atorvastatin 40mg",          "route": "Oral", "frequency": "Nightly",  "classification": "Statin"},
    {"name": "Aspirin 81mg",               "route": "Oral", "frequency": "Daily",    "classification": "Antiplatelet"},
    {"name": "Warfarin 5mg",               "route": "Oral", "frequency": "Daily",    "classification": "Anticoagulant"},
    {"name": "Amlodipine 5mg",             "route": "Oral", "frequency": "Daily",    "classification": "Calcium Channel Blocker"},
    {"name": "Omeprazole 20mg",            "route": "Oral", "frequency": "Daily",    "classification": "PPI"},
    {"name": "Gabapentin 300mg",           "route": "Oral", "frequency": "TID",      "classification": "Anticonvulsant"},
    {"name": "Insulin Glargine 20 units",  "route": "Subcutaneous", "frequency": "Nightly", "classification": "Insulin"},
    {"name": "Albuterol Inhaler",          "route": "Inhalation", "frequency": "PRN", "classification": "Bronchodilator"},
    {"name": "Sertraline 50mg",            "route": "Oral", "frequency": "Daily",    "classification": "SSRI"},
    {"name": "Tamsulosin 0.4mg",           "route": "Oral", "frequency": "Daily",    "classification": "Alpha Blocker"},
    {"name": "Levothyroxine 50mcg",        "route": "Oral", "frequency": "Daily",    "classification": "Thyroid"},
]

# ── Allergies Pool ─────────────────────────────────────────────────────────

ALLERGIES_POOL = [
    {"allergy": "Penicillin",   "reaction": "Rash",               "severity": 2},
    {"allergy": "Sulfa drugs",  "reaction": "Hives",              "severity": 2},
    {"allergy": "Codeine",      "reaction": "Nausea/vomiting",    "severity": 1},
    {"allergy": "Aspirin",      "reaction": "GI bleeding",        "severity": 3},
    {"allergy": "Latex",        "reaction": "Contact dermatitis", "severity": 2},
    {"allergy": "Shellfish",    "reaction": "Anaphylaxis",        "severity": 3},
    {"allergy": "Ibuprofen",    "reaction": "GI upset",           "severity": 1},
    {"allergy": "Morphine",     "reaction": "Excessive sedation", "severity": 2},
]

# ── Caregiver Skill Disciplines ────────────────────────────────────────────

DISCIPLINES = {
    "RN":  {"id": 1, "name": "Registered Nurse",         "hourly_rate": 45},
    "LPN": {"id": 2, "name": "Licensed Practical Nurse", "hourly_rate": 30},
    "PT":  {"id": 3, "name": "Physical Therapist",       "hourly_rate": 55},
    "OT":  {"id": 4, "name": "Occupational Therapist",   "hourly_rate": 55},
    "ST":  {"id": 5, "name": "Speech Therapist",         "hourly_rate": 55},
    "HHA": {"id": 6, "name": "Home Health Aide",         "hourly_rate": 18},
    "MSW": {"id": 7, "name": "Medical Social Worker",    "hourly_rate": 35},
}

# ══════════════════════════════════════════════════════════════════════════════
# CAREGIVERS — 15 staff members
# ══════════════════════════════════════════════════════════════════════════════

CAREGIVERS = [
    {
        "id": uid(),
        "firstName": "Patricia",
        "lastName": "Williams",
        "discipline": "RN",
        "disciplineId": 1,
        "licenseNumber": "IL-RN-284719",
        "licenseExpiry": days_from_now(280),
        "phone": "708-555-0101",
        "email": "p.williams@careops.ai",
        "address": "14 Oak Lane, Oak Forest, IL 60452",
        "latitude": 41.6220,
        "longitude": -87.7510,
        "maxPatientsPerDay": 6,
        "availableDays": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
        "shiftStart": "08:00",
        "shiftEnd": "17:00",
        "skills": ["wound_care", "iv_therapy", "diabetes_management", "cardiac_monitoring"],
        "yearsExperience": 12,
        "status": "active",
        "cpxExpiry": days_from_now(180),
        "tbTestExpiry": days_from_now(200),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "Marcus",
        "lastName": "Johnson",
        "discipline": "RN",
        "disciplineId": 1,
        "licenseNumber": "IL-RN-391047",
        "licenseExpiry": days_from_now(95),   # ← expiring soon — compliance alert
        "phone": "708-555-0102",
        "email": "m.johnson@careops.ai",
        "address": "287 Elm St, Tinley Park, IL 60477",
        "latitude": 41.5760,
        "longitude": -87.7840,
        "maxPatientsPerDay": 5,
        "availableDays": ["Monday","Tuesday","Thursday","Friday","Saturday"],
        "shiftStart": "07:00",
        "shiftEnd": "16:00",
        "skills": ["wound_care", "foley_catheter", "ostomy_care", "post_surgical"],
        "yearsExperience": 8,
        "status": "active",
        "cpxExpiry": days_from_now(365),
        "tbTestExpiry": days_from_now(300),
        "isOnCall": True,
    },
    {
        "id": uid(),
        "firstName": "Denise",
        "lastName": "Carter",
        "discipline": "LPN",
        "disciplineId": 2,
        "licenseNumber": "IL-LPN-104823",
        "licenseExpiry": days_from_now(340),
        "phone": "708-555-0103",
        "email": "d.carter@careops.ai",
        "address": "55 Maple Ave, Homewood, IL 60430",
        "latitude": 41.5610,
        "longitude": -87.6640,
        "maxPatientsPerDay": 7,
        "availableDays": ["Monday","Wednesday","Thursday","Friday"],
        "shiftStart": "09:00",
        "shiftEnd": "17:00",
        "skills": ["medication_management", "vitals", "wound_care_basic"],
        "yearsExperience": 5,
        "status": "active",
        "cpxExpiry": days_from_now(250),
        "tbTestExpiry": days_from_now(190),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "Robert",
        "lastName": "Thompson",
        "discipline": "PT",
        "disciplineId": 3,
        "licenseNumber": "IL-PT-557291",
        "licenseExpiry": days_from_now(410),
        "phone": "708-555-0104",
        "email": "r.thompson@careops.ai",
        "address": "901 Pine Rd, Frankfort, IL 60423",
        "latitude": 41.4990,
        "longitude": -87.8480,
        "maxPatientsPerDay": 8,
        "availableDays": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
        "shiftStart": "08:00",
        "shiftEnd": "17:00",
        "skills": ["gait_training", "transfer_training", "therapeutic_exercise", "fall_prevention", "hip_replacement_rehab", "knee_replacement_rehab"],
        "yearsExperience": 15,
        "status": "active",
        "cpxExpiry": days_from_now(310),
        "tbTestExpiry": days_from_now(270),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "Angela",
        "lastName": "Davis",
        "discipline": "PT",
        "disciplineId": 3,
        "licenseNumber": "IL-PT-448812",
        "licenseExpiry": days_from_now(185),
        "phone": "708-555-0105",
        "email": "a.davis@careops.ai",
        "address": "33 Birch Blvd, Matteson, IL 60443",
        "latitude": 41.5080,
        "longitude": -87.7160,
        "maxPatientsPerDay": 7,
        "availableDays": ["Tuesday","Wednesday","Thursday","Friday","Saturday"],
        "shiftStart": "09:00",
        "shiftEnd": "18:00",
        "skills": ["stroke_rehab", "balance_training", "wheelchair_assessment", "neurological_rehab"],
        "yearsExperience": 9,
        "status": "active",
        "cpxExpiry": days_from_now(200),
        "tbTestExpiry": days_from_now(145),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "Kevin",
        "lastName": "Martinez",
        "discipline": "OT",
        "disciplineId": 4,
        "licenseNumber": "IL-OT-223947",
        "licenseExpiry": days_from_now(520),
        "phone": "708-555-0106",
        "email": "k.martinez@careops.ai",
        "address": "1204 Cedar Dr, Orland Park, IL 60462",
        "latitude": 41.6050,
        "longitude": -87.8520,
        "maxPatientsPerDay": 6,
        "availableDays": ["Monday","Tuesday","Wednesday","Friday"],
        "shiftStart": "08:00",
        "shiftEnd": "16:00",
        "skills": ["adl_training", "adaptive_equipment", "home_modification", "cognitive_rehab", "upper_extremity_rehab"],
        "yearsExperience": 11,
        "status": "active",
        "cpxExpiry": days_from_now(400),
        "tbTestExpiry": days_from_now(380),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "Sandra",
        "lastName": "Wilson",
        "discipline": "HHA",
        "disciplineId": 6,
        "licenseNumber": "IL-HHA-889234",
        "licenseExpiry": days_from_now(220),
        "phone": "708-555-0107",
        "email": "s.wilson@careops.ai",
        "address": "78 Willow St, Harvey, IL 60426",
        "latitude": 41.6120,
        "longitude": -87.6490,
        "maxPatientsPerDay": 5,
        "availableDays": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
        "shiftStart": "07:00",
        "shiftEnd": "15:00",
        "skills": ["personal_care", "bathing_assistance", "meal_prep", "light_housekeeping", "mobility_assistance"],
        "yearsExperience": 6,
        "status": "active",
        "cpxExpiry": days_from_now(150),
        "tbTestExpiry": days_from_now(130),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "James",
        "lastName": "Anderson",
        "discipline": "HHA",
        "disciplineId": 6,
        "licenseNumber": "IL-HHA-774519",
        "licenseExpiry": days_from_now(30),   # ← EXPIRING IN 30 DAYS — urgent alert
        "phone": "708-555-0108",
        "email": "j.anderson@careops.ai",
        "address": "445 Ash Ave, Lansing, IL 60438",
        "latitude": 41.5660,
        "longitude": -87.5400,
        "maxPatientsPerDay": 6,
        "availableDays": ["Monday","Wednesday","Thursday","Friday","Saturday"],
        "shiftStart": "08:00",
        "shiftEnd": "16:00",
        "skills": ["personal_care", "bathing_assistance", "companionship", "medication_reminders", "mobility_assistance"],
        "yearsExperience": 3,
        "status": "active",
        "cpxExpiry": days_from_now(180),
        "tbTestExpiry": days_from_now(210),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "Michelle",
        "lastName": "Brown",
        "discipline": "RN",
        "disciplineId": 1,
        "licenseNumber": "IL-RN-601248",
        "licenseExpiry": days_from_now(390),
        "phone": "708-555-0109",
        "email": "m.brown@careops.ai",
        "address": "219 Spruce Ln, Dolton, IL 60419",
        "latitude": 41.6290,
        "longitude": -87.6100,
        "maxPatientsPerDay": 6,
        "availableDays": ["Tuesday","Wednesday","Thursday","Friday","Saturday"],
        "shiftStart": "10:00",
        "shiftEnd": "19:00",
        "skills": ["iv_therapy", "picc_line_care", "wound_care", "oncology", "palliative_care"],
        "yearsExperience": 14,
        "status": "active",
        "cpxExpiry": days_from_now(320),
        "tbTestExpiry": days_from_now(290),
        "isOnCall": True,
    },
    {
        "id": uid(),
        "firstName": "David",
        "lastName": "Lee",
        "discipline": "ST",
        "disciplineId": 5,
        "licenseNumber": "IL-ST-334782",
        "licenseExpiry": days_from_now(445),
        "phone": "708-555-0110",
        "email": "d.lee@careops.ai",
        "address": "87 Poplar Ct, Flossmoor, IL 60422",
        "latitude": 41.5400,
        "longitude": -87.6840,
        "maxPatientsPerDay": 5,
        "availableDays": ["Monday","Tuesday","Wednesday","Thursday"],
        "shiftStart": "08:00",
        "shiftEnd": "16:00",
        "skills": ["dysphagia_treatment", "aphasia_therapy", "cognitive_communication", "voice_therapy"],
        "yearsExperience": 7,
        "status": "active",
        "cpxExpiry": days_from_now(350),
        "tbTestExpiry": days_from_now(310),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "Tanya",
        "lastName": "Robinson",
        "discipline": "MSW",
        "disciplineId": 7,
        "licenseNumber": "IL-MSW-112938",
        "licenseExpiry": days_from_now(500),
        "phone": "708-555-0111",
        "email": "t.robinson@careops.ai",
        "address": "332 Locust St, Park Forest, IL 60466",
        "latitude": 41.4850,
        "longitude": -87.6760,
        "maxPatientsPerDay": 8,
        "availableDays": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
        "shiftStart": "09:00",
        "shiftEnd": "17:00",
        "skills": ["care_coordination", "community_resources", "caregiver_support", "advance_directives", "mental_health_assessment"],
        "yearsExperience": 10,
        "status": "active",
        "cpxExpiry": days_from_now(420),
        "tbTestExpiry": days_from_now(400),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "Carlos",
        "lastName": "Garcia",
        "discipline": "LPN",
        "disciplineId": 2,
        "licenseNumber": "IL-LPN-228847",
        "licenseExpiry": days_from_now(260),
        "phone": "708-555-0112",
        "email": "c.garcia@careops.ai",
        "address": "156 Chestnut Blvd, Calumet City, IL 60409",
        "latitude": 41.6170,
        "longitude": -87.5320,
        "maxPatientsPerDay": 7,
        "availableDays": ["Monday","Tuesday","Wednesday","Friday","Saturday"],
        "shiftStart": "06:00",
        "shiftEnd": "14:00",
        "skills": ["medication_management", "vitals", "diabetic_foot_care", "blood_draws"],
        "yearsExperience": 4,
        "status": "active",
        "cpxExpiry": days_from_now(200),
        "tbTestExpiry": days_from_now(175),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "Lisa",
        "lastName": "Taylor",
        "discipline": "HHA",
        "disciplineId": 6,
        "licenseNumber": "IL-HHA-991037",
        "licenseExpiry": days_from_now(310),
        "phone": "708-555-0113",
        "email": "l.taylor@careops.ai",
        "address": "509 Oak Park Ave, Richton Park, IL 60471",
        "latitude": 41.4850,
        "longitude": -87.7390,
        "maxPatientsPerDay": 5,
        "availableDays": ["Tuesday","Wednesday","Thursday","Saturday","Sunday"],
        "shiftStart": "08:00",
        "shiftEnd": "16:00",
        "skills": ["personal_care", "bathing_assistance", "dementia_care", "fall_prevention_assist"],
        "yearsExperience": 8,
        "status": "active",
        "cpxExpiry": days_from_now(280),
        "tbTestExpiry": days_from_now(255),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "William",
        "lastName": "Harris",
        "discipline": "RN",
        "disciplineId": 1,
        "licenseNumber": "IL-RN-447182",
        "licenseExpiry": days_from_now(150),
        "phone": "708-555-0114",
        "email": "w.harris@careops.ai",
        "address": "771 Walnut Rd, Chicago Heights, IL 60411",
        "latitude": 41.5080,
        "longitude": -87.6370,
        "maxPatientsPerDay": 5,
        "availableDays": ["Monday","Tuesday","Wednesday","Thursday"],
        "shiftStart": "07:00",
        "shiftEnd": "15:00",
        "skills": ["wound_care", "ostomy_care", "tracheostomy_care", "ventilator_management"],
        "yearsExperience": 20,
        "status": "active",
        "cpxExpiry": days_from_now(100),
        "tbTestExpiry": days_from_now(320),
        "isOnCall": False,
    },
    {
        "id": uid(),
        "firstName": "Keisha",
        "lastName": "Moore",
        "discipline": "OT",
        "disciplineId": 4,
        "licenseNumber": "IL-OT-338821",
        "licenseExpiry": days_from_now(475),
        "phone": "708-555-0115",
        "email": "k.moore@careops.ai",
        "address": "28 Sycamore Dr, Olympia Fields, IL 60461",
        "latitude": 41.5150,
        "longitude": -87.6920,
        "maxPatientsPerDay": 6,
        "availableDays": ["Monday","Wednesday","Thursday","Friday"],
        "shiftStart": "09:00",
        "shiftEnd": "17:00",
        "skills": ["adl_training", "home_safety_evaluation", "low_vision_rehab", "hand_therapy", "cognitive_rehab"],
        "yearsExperience": 6,
        "status": "active",
        "cpxExpiry": days_from_now(390),
        "tbTestExpiry": days_from_now(350),
        "isOnCall": False,
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# PATIENTS — 50 active patients with full clinical data
# ══════════════════════════════════════════════════════════════════════════════

def make_patient(
    first, last, age, gender, loc_idx,
    primary_dx_idx, secondary_dx_indices,
    med_indices, allergy_indices,
    discipline_needed, visits_per_week,
    admission_days_ago, payer="Medicare",
    preferred_caregiver_name=None,
):
    loc = CHICAGO_LOCATIONS[loc_idx % len(CHICAGO_LOCATIONS)]
    primary_dx = COMMON_DIAGNOSES[primary_dx_idx]
    dob = (datetime.now() - timedelta(days=age*365)).isoformat() + "Z"
    admission = days_ago(admission_days_ago)
    episode_start = days_ago(admission_days_ago)
    # Episode is 60 days, calculate period
    days_into_episode = admission_days_ago % 60
    episode_end = days_from_now(60 - days_into_episode)

    diagnoses = [
        {
            "description": primary_dx["description"],
            "code": primary_dx["code"],
            "order": 0,
            "startDate": admission,
            "resolvedDate": None,
            "isRelated": True,
            "notRelatedComments": None,
        }
    ]
    for order, idx in enumerate(secondary_dx_indices, 1):
        dx = COMORBIDITIES[idx % len(COMORBIDITIES)]
        diagnoses.append({
            "description": dx["description"],
            "code": dx["code"],
            "order": order,
            "startDate": admission,
            "resolvedDate": None,
            "isRelated": True,
            "notRelatedComments": None,
        })

    medications = []
    for med_idx in med_indices:
        med = MEDICATIONS_POOL[med_idx % len(MEDICATIONS_POOL)]
        medications.append({
            "id": uid(),
            "medicationName": med["name"],
            "route": med["route"],
            "frequency": med["frequency"],
            "classification": med["classification"],
            "startDate": admission,
            "discontinueDate": None,
            "isPrn": med["frequency"] == "PRN",
            "isRelated": True,
            "isCovered": True,
            "addedByPhysician": "Dr. Sarah Chen",
            "dosage": med["name"].split(" ")[-1] if any(c.isdigit() for c in med["name"]) else "Per order",
        })

    allergies = []
    for al_idx in allergy_indices:
        al = ALLERGIES_POOL[al_idx % len(ALLERGIES_POOL)]
        allergies.append({
            "id": uid(),
            "allergy": al["allergy"],
            "reaction": al["reaction"],
            "severity": al["severity"],
            "type": 1,
            "startDate": days_ago(365),
            "endDate": None,
        })

    patient_id = uid()
    admission_id = uid()

    return {
        # ── Axxess search result shape ──────────────────────────────────────
        "search": {
            "patientId": patient_id,
            "admissionId": admission_id,
            "branchId": uid(),
            "firstName": first,
            "lastName": last,
            "middleInitial": "",
            "medicalRecordNumber": f"MRN-{str(hash(first+last))[-6:]}",
            "dateOfBirth": dob,
            "status": 1,
            "lineOfService": 1,
        },
        # ── Axxess patient detail shape ─────────────────────────────────────
        "detail": {
            "id": patient_id,
            "branchId": uid(),
            "firstName": first,
            "lastName": last,
            "middleInitial": "",
            "latestAdmissionId": admission_id,
            "medicalRecordNumber": f"MRN-{str(hash(first+last))[-6:]}",
            "gender": 1 if gender == "M" else 2,
            "dateOfBirth": dob,
            "addressLine1": f"{random.randint(100, 9999)} {random.choice(['Main','Oak','Elm','Maple','Cedar'])} {random.choice(['St','Ave','Dr','Blvd','Ln'])}",
            "addressLine2": "",
            "city": loc["neighborhood"],
            "state": "IL",
            "zipCode": "60452",
            "latitude": loc["lat"] + random.uniform(-0.01, 0.01),
            "longitude": loc["lng"] + random.uniform(-0.01, 0.01),
            "preferredPhone": f"708-555-{random.randint(1000,9999)}",
            "medicareNumber": f"1{str(hash(first))[-8:][:9]}A" if payer in ["Medicare","Medicare Advantage"] else None,
            "medicareBeneficiaryIdentification": f"{str(hash(last))[-11:].upper()}" if payer in ["Medicare","Medicare Advantage"] else None,
            "medicaidNumber": f"IL{str(hash(first+last))[-8:]}" if payer == "Medicaid" else None,
            "primaryPayorName": payer,
            "benefitPeriodStartDate": episode_start,
            "benefitPeriodEndDate": episode_end,
            "isTransfer": False,
            "isReAdmit": random.random() < 0.15,
            "admissionDate": admission,
            "levelOfCare": 1,
            "lineOfService": 1,
            "isDoNotResuscitate": age > 80 and random.random() < 0.3,
            "isHospitalized": False,
            "showAuthorizations": True,
            "attendingPhysicianId": uid(),
            "attendingPhysicianName": random.choice([
                "Dr. Sarah Chen", "Dr. Michael Okonkwo",
                "Dr. Jennifer Patel", "Dr. Robert Vasquez",
                "Dr. Patricia Kim"
            ]),
            "referralId": uid(),
            "referralDate": days_ago(admission_days_ago + 3),
            "status": 1,
            "statusReason": "",
            "diagnoses": diagnoses,
            "patientTags": [],
            "veterans": [],
            "pendingReason": 0,
            "pendingReasonComment": "",
        },
        # ── Medications (separate endpoint) ─────────────────────────────────
        "medications": medications,
        # ── Allergies (separate endpoint) ───────────────────────────────────
        "allergies": allergies,
        # ── Care plan (separate endpoint) ───────────────────────────────────
        "care_plan": [
            {
                "id": uid(),
                "name": f"{primary_dx['pdgm_group']} Care",
                "statements": [
                    {
                        "id": uid(),
                        "statement": f"Patient presents with {primary_dx['description'].lower()} requiring skilled nursing intervention.",
                        "effectiveDate": admission,
                        "goals": [
                            {
                                "id": uid(),
                                "goal": "Patient will demonstrate improved functional status within 60 days.",
                                "effectiveDate": admission,
                            }
                        ],
                        "interventions": [
                            {
                                "id": uid(),
                                "intervention": "Skilled nursing assessment and monitoring of condition.",
                                "disciplines": [discipline_needed],
                                "effectiveDate": admission,
                            },
                            {
                                "id": uid(),
                                "intervention": "Patient and caregiver education regarding disease process and management.",
                                "disciplines": [discipline_needed],
                                "effectiveDate": admission,
                            }
                        ],
                    }
                ]
            }
        ],
        # ── CareOps-specific metadata (not from Axxess) ─────────────────────
        "_careops": {
            "patientId": patient_id,
            "disciplineNeeded": discipline_needed,
            "visitsPerWeek": visits_per_week,
            "pdgmGroup": primary_dx["pdgm_group"],
            "primaryIcd10": primary_dx["code"],
            "daysIntoEpisode": days_into_episode,
            "episodeEndsAt": episode_end,
            "visitsThisEpisode": random.randint(
                visits_per_week * (days_into_episode // 7),
                visits_per_week * (days_into_episode // 7) + visits_per_week
            ),
            "visitsRequired": visits_per_week * 8,  # 8 weeks per 60-day episode
            "lupaThreshold": max(2, visits_per_week - 1),  # min visits to avoid LUPA
            "preferredCaregiver": preferred_caregiver_name,
            "authorizationStatus": random.choice(["approved","approved","approved","pending"]),
            "authVisitsApproved": visits_per_week * 8 + random.randint(0,4),
            "noaFiled": True,
            "noaDate": days_ago(admission_days_ago - 2),
        }
    }


# Build all 50 patients
PATIENTS = [
    make_patient("Dorothy", "Williams",    78, "F",  0, 0,  [0,1,2],    [0,1,4,8],  [0],   1, 3, 45),
    make_patient("Harold",  "Johnson",     82, "M",  1, 1,  [1,2,3],    [1,2,5],    [1],   1, 2, 38),
    make_patient("Evelyn",  "Davis",       71, "F",  2, 2,  [2,3],      [3,4,6],    [2],   3, 3, 22),
    make_patient("Walter",  "Anderson",    75, "M",  3, 3,  [0,2,4],    [0,5,9],    [],    3, 3, 15),
    make_patient("Ruth",    "Martinez",    68, "F",  4, 4,  [1,3],      [1,2,7],    [0,1], 3, 2, 55),
    make_patient("Eugene",  "Thomas",      80, "M",  5, 5,  [0,1,5],    [0,3,11],   [],    1, 3, 12),
    make_patient("Mildred", "Jackson",     73, "F",  6, 6,  [2,4],      [4,8,12],   [2],   1, 2, 28),
    make_patient("Arthur",  "White",       85, "M",  7, 7,  [1,3,5],    [0,1,6,13], [0],   1, 3, 8),
    make_patient("Frances", "Harris",      66, "F",  8, 8,  [0,2],      [2,9,14],   [3],   6, 5, 42),
    make_patient("Raymond", "Martin",      79, "M",  9, 9,  [1,4],      [0,3,5],    [],    1, 2, 19),
    make_patient("Gloria",  "Garcia",      72, "F",  10, 10, [0,2,3],   [1,4,7],    [1],   3, 3, 31),
    make_patient("Howard",  "Miller",      88, "M",  11, 11, [1,5],     [0,2,8],    [0,2], 4, 2, 7),
    make_patient("Phyllis", "Wilson",      69, "F",  12, 12, [2,4],     [3,6,10],   [],    3, 3, 48),
    make_patient("Bernard", "Moore",       76, "M",  13, 0,  [0,1,6],   [0,1,3,9],  [1],   1, 3, 25),
    make_patient("Norma",   "Taylor",      83, "F",  14, 1,  [2,3,4],   [2,5,11],   [0],   1, 2, 14),
    make_patient("Earl",    "Brown",       77, "M",  0,  2,  [0,5],     [1,4,6],    [2],   1, 3, 36),
    make_patient("Virginia","Jackson",     70, "F",  1,  3,  [1,3],     [0,3,7],    [],    3, 4, 20),
    make_patient("Herman",  "Lee",         84, "M",  2,  4,  [2,4,5],   [1,2,8],    [1],   4, 2, 9),
    make_patient("Edna",    "Perez",       67, "F",  3,  5,  [0,2],     [4,9,13],   [0],   1, 3, 52),
    make_patient("Stanley", "Thompson",    81, "M",  4,  6,  [1,3,4],   [0,3,5,12], [2],   1, 2, 17),
    make_patient("Beatrice","Robinson",    74, "F",  5,  7,  [2,5],     [1,6,14],   [],    6, 4, 33),
    make_patient("Leonard", "Clark",       78, "M",  6,  8,  [0,1,3],   [2,4,7],    [1],   1, 3, 11),
    make_patient("Marjorie","Rodriguez",   71, "F",  7,  9,  [2,4],     [0,5,8],    [0,3], 3, 2, 44),
    make_patient("Clarence","Lewis",       86, "M",  8,  10, [1,3,5],   [3,6,11],   [],    1, 3, 6),
    make_patient("Thelma",  "Walker",      65, "F",  9,  11, [0,2],     [1,4,9],    [2],   4, 3, 58),
    make_patient("Chester", "Hall",        80, "M",  10, 12, [2,4,5],   [0,2,7],    [],    3, 2, 23),
    make_patient("Lois",    "Allen",       73, "F",  11, 0,  [1,3],     [3,5,10],   [1],   1, 4, 16),
    make_patient("Floyd",   "Young",       77, "M",  12, 1,  [0,2,4],   [0,1,6],    [0],   1, 3, 39),
    make_patient("Velma",   "Hernandez",   69, "F",  13, 2,  [1,5],     [2,4,8],    [],    3, 3, 29),
    make_patient("Gordon",  "King",        83, "M",  14, 3,  [2,3,4],   [1,3,7],    [2],   1, 2, 13),
    make_patient("Alberta", "Wright",      76, "F",  0,  4,  [0,2],     [0,5,12],   [1],   6, 5, 47),
    make_patient("Elmer",   "Lopez",       79, "M",  1,  5,  [1,3,5],   [2,4,9],    [],    1, 3, 21),
    make_patient("Hazel",   "Scott",       72, "F",  2,  6,  [2,4],     [3,6,13],   [0],   4, 2, 35),
    make_patient("Alvin",   "Torres",      85, "M",  3,  7,  [0,1,4],   [0,2,5],    [1,2], 1, 3, 10),
    make_patient("Bertha",  "Nguyen",      68, "F",  4,  8,  [2,3],     [1,4,7],    [],    3, 3, 51),
    make_patient("Clifton", "Hill",        81, "M",  5,  9,  [1,5],     [0,3,8],    [0],   1, 2, 18),
    make_patient("Irene",   "Flores",      74, "F",  6,  10, [0,2,4],   [2,5,11],   [2],   6, 4, 32),
    make_patient("Virgil",  "Green",       78, "M",  7,  11, [1,3],     [1,4,6],    [],    3, 3, 26),
    make_patient("Mabel",   "Adams",       83, "F",  8,  12, [2,4,5],   [0,3,9],    [1],   1, 2, 8),
    make_patient("Leroy",   "Nelson",      70, "M",  9,  0,  [0,1,3],   [2,5,10],   [0],   4, 3, 43),
    make_patient("Esther",  "Carter",      77, "F",  10, 1,  [2,4],     [1,6,13],   [],    1, 3, 15),
    make_patient("Cecil",   "Mitchell",    82, "M",  11, 2,  [1,3,5],   [0,4,7],    [2],   3, 2, 37),
    make_patient("Lillian", "Perez",       65, "F",  12, 3,  [0,2],     [3,5,12],   [1],   6, 5, 24),
    make_patient("Melvin",  "Roberts",     79, "M",  13, 4,  [2,4],     [1,2,8],    [],    1, 3, 19),
    make_patient("Agnes",   "Turner",      86, "F",  14, 5,  [1,3,4],   [0,4,9],    [0],   1, 2, 5),
    make_patient("Rufus",   "Phillips",    73, "M",  0,  6,  [0,2,5],   [2,3,7],    [1,2], 3, 3, 30),
    make_patient("Ethel",   "Campbell",    80, "F",  1,  7,  [1,4],     [1,5,10],   [],    4, 2, 22),
    make_patient("Vernon",  "Parker",      75, "M",  2,  8,  [2,3],     [0,2,6],    [0],   1, 3, 41),
    make_patient("Hattie",  "Evans",       69, "F",  3,  9,  [0,1,4],   [3,4,8],    [2],   6, 4, 14),
    make_patient("Sylvester","Edwards",    84, "M",  4,  10, [1,3,5],   [1,2,7],    [],    1, 2, 7),
]

# ══════════════════════════════════════════════════════════════════════════════
# MOCK AXXESS CLIENT — Drop-in replacement for AxxessClient
# ══════════════════════════════════════════════════════════════════════════════

class AxxessMockClient:
    """
    Mock implementation of AxxessClient using the PATIENTS and CAREGIVERS
    data above. Mirrors the exact method signatures of the real client
    so swapping is a one-line change.

    Usage:
        from integrations.axxess.mock import AxxessMockClient
        client = AxxessMockClient()
        patients = await client.search_patients()
    """

    # ── Patient Methods ─────────────────────────────────────────────────────

    async def search_patients(
        self,
        term: str = None,
        date_of_birth: str = None,
        gender: int = None,
        patient_status: int = None,
    ) -> list[dict]:
        results = [p["search"] for p in PATIENTS]
        if term:
            t = term.lower()
            results = [
                r for r in results
                if t in r["firstName"].lower()
                or t in r["lastName"].lower()
                or t in r.get("medicalRecordNumber","").lower()
            ]
        if gender is not None:
            deets = {p["search"]["patientId"]: p["detail"] for p in PATIENTS}
            results = [r for r in results if deets[r["patientId"]]["gender"] == gender]
        return results

    async def get_patient(self, patient_id: str) -> dict:
        for p in PATIENTS:
            if p["detail"]["id"] == patient_id:
                return p["detail"]
        raise ValueError(f"Patient {patient_id} not found in mock data")

    async def get_medications(self, patient_id: str, **kwargs) -> list[dict]:
        for p in PATIENTS:
            if p["detail"]["id"] == patient_id:
                return p["medications"]
        return []

    async def get_allergies(self, patient_id: str, **kwargs) -> list[dict]:
        for p in PATIENTS:
            if p["detail"]["id"] == patient_id:
                return p["allergies"]
        return []

    async def get_care_plan(self, patient_id: str) -> list[dict]:
        for p in PATIENTS:
            if p["detail"]["id"] == patient_id:
                return p["care_plan"]
        return []

    async def get_vitals(self, patient_id: str, **kwargs) -> dict:
        return {
            "itemCount": 0, "pageLength": 50,
            "currentPage": 1, "pageCount": 0, "items": []
        }

    async def get_full_patient_profile(self, patient_id: str) -> dict:
        from datetime import datetime
        for p in PATIENTS:
            if p["detail"]["id"] == patient_id:
                return {
                    "patient": p["detail"],
                    "care_plan": p["care_plan"],
                    "medications": p["medications"],
                    "allergies": p["allergies"],
                    "vitals": {"itemCount":0,"pageLength":50,"currentPage":1,"pageCount":0,"items":[]},
                    "pulled_at": datetime.now().isoformat(),
                }
        raise ValueError(f"Patient {patient_id} not found")

    # ── Caregiver Methods (CareOps-native, not from Axxess) ─────────────────

    async def get_caregivers(self) -> list[dict]:
        return CAREGIVERS

    async def get_caregiver(self, caregiver_id: str) -> dict:
        for c in CAREGIVERS:
            if c["id"] == caregiver_id:
                return c
        raise ValueError(f"Caregiver {caregiver_id} not found")

    async def get_available_caregivers(self, day_of_week: str, discipline_id: int = None) -> list[dict]:
        results = [c for c in CAREGIVERS if day_of_week in c["availableDays"] and c["status"] == "active"]
        if discipline_id:
            results = [c for c in results if c["disciplineId"] == discipline_id]
        return results

    # ── CareOps Metadata ────────────────────────────────────────────────────

    async def get_careops_patient_data(self, patient_id: str) -> dict:
        """Get CareOps-specific metadata (not from Axxess API)."""
        for p in PATIENTS:
            if p["detail"]["id"] == patient_id:
                return p["_careops"]
        raise ValueError(f"Patient {patient_id} not found")

    async def get_all_careops_data(self) -> list[dict]:
        """Get all patients with their CareOps metadata — used by scheduling engine."""
        return [
            {
                "patientId": p["detail"]["id"],
                "firstName": p["detail"]["firstName"],
                "lastName": p["detail"]["lastName"],
                "latitude": p["detail"]["latitude"],
                "longitude": p["detail"]["longitude"],
                "city": p["detail"]["city"],
                "primaryPayorName": p["detail"]["primaryPayorName"],
                **p["_careops"]
            }
            for p in PATIENTS
        ]

    # ── Compliance Data ─────────────────────────────────────────────────────

    async def get_expiring_credentials(self, days_threshold: int = 90) -> list[dict]:
        """Get caregivers with credentials expiring within threshold days."""
        from datetime import datetime
        alerts = []
        now = datetime.now()
        for c in CAREGIVERS:
            for field, label in [
                ("licenseExpiry", "License"),
                ("cpxExpiry", "CPR Certification"),
                ("tbTestExpiry", "TB Test"),
            ]:
                expiry_str = c.get(field, "")
                if not expiry_str:
                    continue
                try:
                    expiry = datetime.fromisoformat(expiry_str.replace("Z",""))
                    days_left = (expiry - now).days
                    if days_left <= days_threshold:
                        alerts.append({
                            "caregiverId": c["id"],
                            "caregiverName": f"{c['firstName']} {c['lastName']}",
                            "discipline": c["discipline"],
                            "credentialType": label,
                            "expiryDate": expiry_str,
                            "daysUntilExpiry": days_left,
                            "isExpired": days_left < 0,
                            "isUrgent": days_left <= 30,
                        })
                except Exception:
                    pass
        return sorted(alerts, key=lambda x: x["daysUntilExpiry"])

    async def get_lupa_risk_patients(self) -> list[dict]:
        """Get patients at risk of LUPA (too few visits this period)."""
        at_risk = []
        for p in PATIENTS:
            meta = p["_careops"]
            days_in = meta["daysIntoEpisode"]
            weeks_in = max(1, days_in // 7)
            expected_visits = meta["visitsPerWeek"] * weeks_in
            actual_visits = meta["visitsThisEpisode"]
            shortfall = expected_visits - actual_visits
            if shortfall >= meta["lupaThreshold"]:
                at_risk.append({
                    "patientId": meta["patientId"],
                    "patientName": f"{p['detail']['firstName']} {p['detail']['lastName']}",
                    "pdgmGroup": meta["pdgmGroup"],
                    "visitsThisEpisode": actual_visits,
                    "visitsExpected": expected_visits,
                    "lupaThreshold": meta["lupaThreshold"],
                    "shortfall": shortfall,
                    "episodeEndsAt": meta["episodeEndsAt"],
                    "daysIntoEpisode": days_in,
                    "riskLevel": "HIGH" if shortfall >= meta["lupaThreshold"] * 2 else "MEDIUM",
                })
        return sorted(at_risk, key=lambda x: x["shortfall"], reverse=True)


# ── Singleton ───────────────────────────────────────────────────────────────
mock_client = AxxessMockClient()
