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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/notes/transcribe")
async def transcribe_note_alias(
    audio: UploadFile = File(...),
    patient_id: str = None,
    caregiver_id: str = None,
):
    return await transcribe_note(audio=audio, patient_id=patient_id, caregiver_id=caregiver_id)
