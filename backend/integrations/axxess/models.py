"""
Axxess API Data Models
──────────────────────
Pydantic models that exactly match the Axxess API response shapes
from their certified API documentation.

These models:
1. Validate every API response so bad data fails loudly
2. Give you full type safety and IDE autocomplete throughout the codebase
3. Serve as the contract between the Axxess integration and our AI modules
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


# ── Patient Search Result (patient-by-name-mrn) ────────────────────────────

class PatientSearchResult(BaseModel):
    """
    Returned by GET /api/v1/patients/patient-by-name-mrn
    Lightweight summary — use for search results and lists.
    """
    patient_id: UUID = Field(alias="patientId")
    admission_id: Optional[UUID] = Field(None, alias="admissionId")
    branch_id: Optional[UUID] = Field(None, alias="branchId")
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    middle_initial: Optional[str] = Field(None, alias="middleInitial")
    medical_record_number: Optional[str] = Field(None, alias="medicalRecordNumber")
    date_of_birth: Optional[datetime] = Field(None, alias="dateOfBirth")
    status: Optional[int] = None
    line_of_service: Optional[int] = Field(None, alias="lineOfService")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    class Config:
        populate_by_name = True


# ── Diagnosis ─────────────────────────────────────────────────────────────

class Diagnosis(BaseModel):
    """ICD-10 diagnosis entry on a patient record."""
    description: Optional[str] = None
    code: Optional[str] = None           # ICD-10 code — critical for PDGM grouping
    order: Optional[int] = None          # Primary=0, Secondary=1, etc.
    start_date: Optional[datetime] = Field(None, alias="startDate")
    resolved_date: Optional[datetime] = Field(None, alias="resolvedDate")
    is_related: Optional[bool] = Field(None, alias="isRelated")
    not_related_comments: Optional[str] = Field(None, alias="notRelatedComments")

    class Config:
        populate_by_name = True


# ── Patient Tag ───────────────────────────────────────────────────────────

class PatientTag(BaseModel):
    id: UUID
    name: str


# ── Full Patient Detail (patients/{id}/slim) ──────────────────────────────

class PatientDetail(BaseModel):
    """
    Returned by GET /api/v1/patients/{id}/slim
    Full patient record — everything the scheduling engine and billing
    module need to make decisions.
    """
    id: UUID
    branch_id: Optional[UUID] = Field(None, alias="branchId")
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    middle_initial: Optional[str] = Field(None, alias="middleInitial")
    latest_admission_id: Optional[UUID] = Field(None, alias="latestAdmissionId")
    suffix: Optional[str] = None
    medical_record_number: Optional[str] = Field(None, alias="medicalRecordNumber")

    # Demographics
    gender: Optional[int] = None
    date_of_birth: Optional[datetime] = Field(None, alias="dateOfBirth")

    # Address & Location (used by scheduling engine for geo-matching)
    address_line1: Optional[str] = Field(None, alias="addressLine1")
    address_line2: Optional[str] = Field(None, alias="addressLine2")
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = Field(None, alias="zipCode")
    longitude: Optional[float] = None   # ← scheduling engine uses these
    latitude: Optional[float] = None    # ← scheduling engine uses these

    # Contact
    preferred_phone: Optional[str] = Field(None, alias="preferredPhone")

    # Insurance (critical for billing and authorization)
    medicare_number: Optional[str] = Field(None, alias="medicareNumber")
    medicare_beneficiary_identification: Optional[str] = Field(
        None, alias="medicareBeneficiaryIdentification"
    )
    medicaid_number: Optional[str] = Field(None, alias="medicaidNumber")
    primary_payor_name: Optional[str] = Field(None, alias="primaryPayorName")

    # Episode Info
    benefit_period_start_date: Optional[datetime] = Field(
        None, alias="benefitPeriodStartDate"
    )
    benefit_period_end_date: Optional[datetime] = Field(
        None, alias="benefitPeriodEndDate"
    )
    transfer_benefit_period_start_date: Optional[datetime] = Field(
        None, alias="transferBenefitPeriodStartDate"
    )
    is_transfer: Optional[bool] = Field(None, alias="isTransfer")
    is_re_admit: Optional[bool] = Field(None, alias="isReAdmit")
    admission_date: Optional[datetime] = Field(None, alias="admissionDate")

    # Clinical flags
    level_of_care: Optional[int] = Field(None, alias="levelOfCare")
    line_of_service: Optional[int] = Field(None, alias="lineOfService")
    is_do_not_resuscitate: Optional[bool] = Field(None, alias="isDoNotResuscitate")
    is_hospitalized: Optional[bool] = Field(None, alias="isHospitalized")
    show_authorizations: Optional[bool] = Field(None, alias="showAuthorizations")

    # Diagnoses — ICD-10 codes used by PDGM grouper
    diagnoses: list[Diagnosis] = []

    # Physician
    attending_physician_id: Optional[UUID] = Field(
        None, alias="attendingPhysicianId"
    )
    attending_physician_name: Optional[str] = Field(
        None, alias="attendingPhysicianName"
    )

    # Referral
    referral_id: Optional[UUID] = Field(None, alias="referralId")
    referral_date: Optional[datetime] = Field(None, alias="referralDate")

    # Status
    status: Optional[int] = None
    status_reason: Optional[str] = Field(None, alias="statusReason")
    pending_reason: Optional[int] = Field(None, alias="pendingReason")
    pending_reason_comment: Optional[str] = Field(
        None, alias="pendingReasonComment"
    )

    # Other
    patient_tags: list[PatientTag] = Field([], alias="patientTags")
    veterans: list[int] = []
    asset_id: Optional[UUID] = Field(None, alias="assetId")
    funeral_home_name: Optional[str] = Field(None, alias="funeralHomeName")
    funeral_home_phone_number: Optional[str] = Field(
        None, alias="funeralHomePhoneNumber"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def primary_icd10(self) -> Optional[str]:
        """Primary diagnosis ICD-10 code — used by PDGM grouper."""
        primary = next((d for d in self.diagnoses if d.order == 0), None)
        return primary.code if primary else None

    @property
    def all_icd10_codes(self) -> list[str]:
        """All diagnosis codes — used for comorbidity capture."""
        return [d.code for d in self.diagnoses if d.code]

    @property
    def has_coordinates(self) -> bool:
        """Whether this patient has GPS coordinates for routing."""
        return self.latitude is not None and self.longitude is not None

    class Config:
        populate_by_name = True


# ── Vital Signs ───────────────────────────────────────────────────────────

class VitalSign(BaseModel):
    """Single vital sign measurement."""
    task_id: Optional[UUID] = Field(None, alias="taskId")
    id: UUID
    scheduled_date: Optional[datetime] = Field(None, alias="scheduledDate")
    entered_by: Optional[str] = Field(None, alias="enteredBy")
    task_name: Optional[str] = Field(None, alias="taskName")

    systolic_pressure: Optional[int] = Field(None, alias="systolicPressure")
    diastolic_pressure: Optional[int] = Field(None, alias="diastolicPressure")
    temperature: Optional[float] = None
    respiration: Optional[int] = None
    oxygen_saturation: Optional[float] = Field(None, alias="oxygenSaturation")
    pulse_rate: Optional[int] = Field(None, alias="pulseRate")

    pulse_location: Optional[int] = Field(None, alias="pulseLocation")
    blood_pressure_position: Optional[int] = Field(None, alias="bloodPressurePosition")
    temperature_route: Optional[int] = Field(None, alias="temperatureRoute")
    fahrenheit_or_celsius: Optional[int] = Field(None, alias="fahrenheitOrCelsius")
    oxygen_method: Optional[int] = Field(None, alias="oxygenMethod")
    unable_to_obtain_bp: Optional[bool] = Field(None, alias="unableToObtainBP")
    unable_to_obtain_pulse: Optional[bool] = Field(None, alias="unableToObtainPulse")

    class Config:
        populate_by_name = True


class VitalsPage(BaseModel):
    """Paginated vital signs response."""
    item_count: int = Field(alias="itemCount")
    page_length: int = Field(alias="pageLength")
    current_page: int = Field(alias="currentPage")
    page_count: int = Field(alias="pageCount")
    items: list[VitalSign] = []

    class Config:
        populate_by_name = True


# ── Care Plan ─────────────────────────────────────────────────────────────

class Goal(BaseModel):
    id: UUID
    goal: str
    problem_id: Optional[UUID] = Field(None, alias="problemId")
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    user_id: Optional[UUID] = Field(None, alias="userId")
    completed_by: Optional[int] = Field(None, alias="completedBy")
    effective_date: Optional[datetime] = Field(None, alias="effectiveDate")

    class Config:
        populate_by_name = True


class Intervention(BaseModel):
    id: UUID
    intervention: str
    problem_id: Optional[UUID] = Field(None, alias="problemId")
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    user_id: Optional[UUID] = Field(None, alias="userId")
    disciplines: list[int] = []  # discipline enum values
    effective_date: Optional[datetime] = Field(None, alias="effectiveDate")

    class Config:
        populate_by_name = True


class ProblemStatement(BaseModel):
    id: UUID
    area_id: Optional[UUID] = Field(None, alias="areaId")
    problem_id: Optional[UUID] = Field(None, alias="problemId")
    document_id: Optional[UUID] = Field(None, alias="documentId")
    statement: str
    effective_date: Optional[datetime] = Field(None, alias="effectiveDate")
    goals: list[Goal] = []
    interventions: list[Intervention] = []
    user_id: Optional[UUID] = Field(None, alias="userId")
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")

    class Config:
        populate_by_name = True


class CarePlanArea(BaseModel):
    id: UUID
    name: str
    statements: list[ProblemStatement] = []

    class Config:
        populate_by_name = True


# ── Medications ───────────────────────────────────────────────────────────

class ClinicalUser(BaseModel):
    id: Optional[UUID] = None
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")

    class Config:
        populate_by_name = True


class Medication(BaseModel):
    id: UUID
    lexi_drug_id: Optional[str] = Field(None, alias="lexiDrugId")
    custom_medication_id: Optional[UUID] = Field(None, alias="customMedicationId")
    start_date: Optional[datetime] = Field(None, alias="startDate")
    medication_name: str = Field(alias="medicationName")
    frequency: Optional[str] = None
    medication_frequency_id: Optional[UUID] = Field(None, alias="medicationFrequencyId")
    is_prn: Optional[bool] = Field(None, alias="isPrn")
    instructions: Optional[str] = None
    dosage: Optional[str] = None
    route: Optional[str] = None
    classification: Optional[str] = None
    discontinue_date: Optional[datetime] = Field(None, alias="discontinueDate")
    initial_physician_id: Optional[UUID] = Field(None, alias="initialPhysicianId")
    discontinue_order_id: Optional[UUID] = Field(None, alias="discontinueOrderId")
    add_by_physician: Optional[str] = Field(None, alias="addedByPhysician")
    discontinued_by_physician: Optional[str] = Field(
        None, alias="discontinuedByPhysician"
    )
    administered_by: list[int] = Field([], alias="administeredBy")
    indication: Optional[str] = None
    is_covered: Optional[bool] = Field(None, alias="isCovered")
    dispense_count: Optional[int] = Field(None, alias="dispenseCount")
    added_by: Optional[ClinicalUser] = Field(None, alias="addedBy")
    discontinued_by: Optional[ClinicalUser] = Field(None, alias="discontinuedBy")
    is_related: Optional[bool] = Field(None, alias="isRelated")
    not_related_comments: Optional[str] = Field(None, alias="notRelatedComments")
    is_from_order_set: Optional[bool] = Field(None, alias="isFromOrderSet")

    class Config:
        populate_by_name = True


# ── Allergies ─────────────────────────────────────────────────────────────

class Allergy(BaseModel):
    id: UUID
    patient_id: Optional[UUID] = Field(None, alias="patientId")
    allergy: str
    reaction: Optional[str] = None
    type: Optional[int] = None
    other_type_description: Optional[str] = Field(None, alias="otherTypeDescription")
    severity: Optional[int] = None
    comments: Optional[str] = None
    information_source: Optional[str] = Field(None, alias="informationSource")
    discontinued_by_id: Optional[UUID] = Field(None, alias="discontinuedById")
    start_date: Optional[datetime] = Field(None, alias="startDate")
    end_date: Optional[datetime] = Field(None, alias="endDate")
    lexi_drug_id: Optional[str] = Field(None, alias="lexiDrugId")
    synonym_id: Optional[int] = Field(None, alias="synonymId")
    custom_medication_id: Optional[UUID] = Field(None, alias="customMedicationId")

    @property
    def is_active(self) -> bool:
        return self.end_date is None

    class Config:
        populate_by_name = True


# ── Unified Patient Profile ───────────────────────────────────────────────

class PatientProfile(BaseModel):
    """
    Combined patient profile pulled from multiple Axxess endpoints.
    This is what the scheduling engine, documentation AI, and
    billing module all work from — one unified object.
    """
    patient: PatientDetail
    care_plan: list[CarePlanArea] = []
    medications: list[Medication] = []
    allergies: list[Allergy] = []
    vitals: Optional[VitalsPage] = None
    pulled_at: str

    @property
    def active_medications(self) -> list[Medication]:
        return [m for m in self.medications if not m.discontinue_date]

    @property
    def active_allergies(self) -> list[Allergy]:
        return [a for a in self.allergies if a.is_active]

    @property
    def medication_names(self) -> list[str]:
        return [m.medication_name for m in self.active_medications]

    @property
    def primary_diagnosis(self) -> Optional[Diagnosis]:
        return next(
            (d for d in self.patient.diagnoses if d.order == 0), None
        )
