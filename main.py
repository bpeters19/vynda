"""
CareOps AI — Backend API
────────────────────────
FastAPI application serving the CareOps AI platform.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CareOps AI",
    description="AI back-office platform for home health agencies",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "CareOps AI"}


# Routers added here as we build each module
# from api.patients import router as patients_router
# from api.schedules import router as schedules_router
# app.include_router(patients_router, prefix="/api/patients")
# app.include_router(schedules_router, prefix="/api/schedules")
