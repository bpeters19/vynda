"""
Vynda — Backend API
"""
import os
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import tempfile
from fastapi import UploadFile, File
from openai import OpenAI
load_dotenv()

app = FastAPI(title="Vynda API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Vynda API", "timestamp": str(date.today())}

@app.post("/api/schedule/generate")
async def trigger_schedule(visit_date: str = None):
    try:
        from scheduler import run_scheduler, save_schedule_to_supabase
        target_date = date.fromisoformat(visit_date) if visit_date else date.today()
        result = run_scheduler(target_date)
        saved = save_schedule_to_supabase(result) if result["scheduled"] else 0
        return {
            "success": True,
            "visit_date": str(target_date),
            "visits_scheduled": result["stats"]["total_scheduled"],
            "visits_saved": saved,
            "coverage_rate": result["stats"]["coverage_rate"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compliance/scan")
async def trigger_compliance_scan():
    try:
        from compliance import run_compliance_scan
        result = run_compliance_scan(write_to_db=True)
        return {
            "success": True,
            "scan_date": result["scan_date"],
            "total_alerts": result["total_alerts"],
            "critical": len([a for a in result["all_alerts"] if a["severity"] == "critical"]),
            "urgent": len([a for a in result["all_alerts"] if a["severity"] == "urgent"]),
            "warning": len([a for a in result["all_alerts"] if a["severity"] == "warning"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync")
async def trigger_sync():
    try:
        from sync import run_sync
        await run_sync()
        return {"success": True, "message": "Sync completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/api/notes/transcribe")
async def transcribe_note(
    audio: UploadFile = File(...),
    patient_id: str = None,
    caregiver_id: str = None,
):
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
        
        # Get agency
        agency = sb.table("agencies").select("id").execute()
        agency_id = agency.data[0]["id"] if agency.data else None

        # Save audio to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio.filename.split('.')[-1]}") as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Transcribe with Whisper
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        
        note_text = transcript.text

        # Save to Supabase
        note = sb.table("visit_notes").insert({
            "agency_id": agency_id,
            "patient_id": patient_id,
            "caregiver_id": caregiver_id,
            "note_text": note_text,
        }).execute()

        # Cleanup temp file
        import os as _os
        _os.unlink(tmp_path)

        return {
            "success": True,
            "note_id": note.data[0]["id"] if note.data else None,
            "transcript": note_text,
        }
    except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")
        
@app.post("/notes/transcribe")
async def transcribe_note_alias(
    audio: UploadFile = File(...),
    patient_id: str = None,
    caregiver_id: str = None,
):
    return await transcribe_note(audio=audio, patient_id=patient_id, caregiver_id=caregiver_id)

@app.post("/api/patients/import")
async def import_patients(patients: list[dict]):
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
        
        agency = sb.table("agencies").select("id").execute()
        agency_id = agency.data[0]["id"] if agency.data else None

        inserted = 0
        errors = []
        for pt in patients:
            try:
                sb.table("patients").insert({
                    "agency_id": agency_id,
                    "first_name": pt.get("first_name", ""),
                    "last_name": pt.get("last_name", ""),
                    "date_of_birth": pt.get("date_of_birth") or None,
                    "city": pt.get("city") or None,
                    "state": pt.get("state") or None,
                    "primary_payor_name": pt.get("primary_payor_name") or None,
                    "primary_icd10": pt.get("primary_icd10") or None,
                    "medical_record_number": pt.get("medical_record_number") or None,
                }).execute()
                inserted += 1
            except Exception as e:
                errors.append(str(e))

        return {
            "success": True,
            "inserted": inserted,
            "errors": errors,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/qa/audit-note")
async def audit_note(
    note_text: str = Form(...),
    patient_id: str = Form(None),
    caregiver_discipline: str = Form(None),
):
    try:
        import anthropic
        from supabase import create_client

        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Pull patient context
        patient_context = ""
        if patient_id:
            pt = sb.table("patients").select(
                "first_name, last_name, primary_icd10, pdgm_group, visits_per_week, discipline_needed"
            ).eq("id", patient_id).execute()

            dx = sb.table("patient_diagnoses").select(
                "icd10_code, description"
            ).eq("patient_id", patient_id).execute()

            meds = sb.table("patient_medications").select(
                "medication_name, dosage, frequency"
            ).eq("patient_id", patient_id).execute()

            if pt.data:
                p = pt.data[0]
                patient_context = f"""
Patient: {p['first_name']} {p['last_name']}
Primary Diagnosis: {p['primary_icd10']} — {p.get('pdgm_group', 'Unknown')}
Visits Per Week: {p['visits_per_week']}
"""
            if dx.data:
                patient_context += "Active Diagnoses:\n"
                for d in dx.data:
                    patient_context += f"  - {d['icd10_code']}: {d['description']}\n"

            if meds.data:
                patient_context += "Current Medications:\n"
                for m in meds.data:
                    patient_context += f"  - {m['medication_name']} {m['dosage']} {m['frequency']}\n"

        discipline = caregiver_discipline or "Unknown"

        prompt = f"""You are a clinical documentation auditor for a home health agency. Your job is to audit visit notes written by caregivers and ensure they meet Medicare documentation standards and align with the patient's plan of care.

PATIENT INFORMATION:
{patient_context if patient_context else "No patient context available."}

CAREGIVER DISCIPLINE: {discipline}

VISIT NOTE TO AUDIT:
{note_text}

Audit this visit note and return a JSON response with exactly this structure:
{{
  "score": <integer 0-100>,
  "grade": "<A, B, C, D, or F>",
  "passed": <true or false>,
  "summary": "<1-2 sentence overall assessment>",
  "flags": [
    {{
      "severity": "<critical, warning, or suggestion>",
      "category": "<e.g. Diagnosis Alignment, Plan of Care, Vitals, Functional Status, Safety, Medication>",
      "message": "<specific actionable finding>"
    }}
  ],
  "strengths": ["<thing the note does well>"],
  "missing_elements": ["<element that should be in this note but is absent>"],
  "recommended_additions": "<1-2 sentences the caregiver should add to improve this note>"
}}

Scoring criteria:
- 90-100 (A): Excellent — addresses primary diagnosis, documents functional status, includes vitals if applicable, follows plan of care, no missing critical elements
- 75-89 (B): Good — mostly complete with minor gaps
- 60-74 (C): Adequate — passes minimum standards but missing important elements
- 40-59 (D): Poor — significant gaps that could cause claim denial or survey findings
- 0-39 (F): Failing — does not meet Medicare documentation standards

Be specific and actionable. Reference the patient's actual diagnoses and medications when flagging issues. Return only valid JSON, no other text."""

        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        import json
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        audit_result = json.loads(raw.strip())

        # Save audit to visit_notes if we have patient_id
        if patient_id:
            sb.table("visit_notes").insert({
                "patient_id": patient_id,
                "note_text": note_text,
                "qa_score": audit_result.get("score"),
                "qa_grade": audit_result.get("grade"),
                "qa_passed": audit_result.get("passed"),
                "qa_flags": json.dumps(audit_result.get("flags", [])),
                "qa_summary": audit_result.get("summary"),
            }).execute()

        return {"success": True, "audit": audit_result}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        
