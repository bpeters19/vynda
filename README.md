# CareOps AI — Backend

AI back-office platform for home health agencies. Built on FastAPI + Supabase, integrating with Axxess EHR via their certified API.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in your credentials in .env
```

## Test Axxess Connection

Once you have API credentials from Axxess:

```bash
python test_axxess.py
```

## Run the API

```bash
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

## Project Structure

```
backend/
├── main.py                    # FastAPI app entry point
├── config.py                  # Settings from .env
├── requirements.txt
├── test_axxess.py             # Connection validation script
│
├── integrations/
│   └── axxess/
│       ├── client.py          # HTTP client + auth token management
│       ├── models.py          # Pydantic models matching API response shapes
│       └── __init__.py
│
├── modules/
│   ├── scheduler/             # AI scheduling engine (next to build)
│   ├── compliance/            # EVV + NOA + LUPA monitoring
│   ├── documentation/         # Voice → structured clinical note
│   └── billing/               # PDGM grouper + claims prep
│
└── api/
    ├── patients.py            # Patient endpoints
    ├── schedules.py           # Schedule endpoints
    ├── compliance.py          # Compliance dashboard
    └── billing.py             # Billing endpoints
```

## Axxess API Endpoints Implemented

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/patients/patient-by-name-mrn` | GET | Search patients |
| `/api/v1/patients/{id}/slim` | GET | Full patient detail |
| `/api/v1/vitalsign` | GET | Patient vitals by date range |
| `/api/v1/poc/{patientId}` | GET | Care plan (problems/goals/interventions) |
| `/api/v1/medications` | GET | Patient medications |
| `/api/v1/allergies` | GET | Patient allergies |
| `/api/v1/fhir/Patient/{id}/$cda-ccds` | GET | Full CCDA clinical summary |

## Next Module: Scheduling Engine

The scheduling engine (`modules/scheduler/engine.py`) will:
1. Pull all active patients with coordinates from Axxess
2. Pull all caregiver availability
3. Match caregivers to patients on: skill, geography, preference, authorization
4. Build optimized daily schedule
5. Monitor EVV in real time and handle call-outs automatically
