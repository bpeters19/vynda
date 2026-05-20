"""
Vynda — Backend API
"""
import os
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
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
