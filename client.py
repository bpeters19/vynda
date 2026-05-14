"""
Axxess API Client
─────────────────
Handles OAuth token lifecycle and all authenticated requests
to the Axxess home health EHR platform.

Auth pattern: Bearer token in Authorization header
Required headers on every request:
  - Authorization: Bearer {token}
  - X-Account-Id: {agency_guid}
  - X-Time-Zone: America/Chicago
"""

import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AxxessAuthError(Exception):
    """Raised when authentication fails."""
    pass


class AxxessAPIError(Exception):
    """Raised when an API call fails."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Axxess API error {status_code}: {message}")


class AxxessClient:
    """
    Authenticated client for the Axxess EHR API.

    Usage:
        client = AxxessClient()
        patient = await client.get_patient_by_id("some-guid")
    """

    def __init__(self):
        self.base_url = settings.axxess_base_url.rstrip("/")
        self.auth_url = settings.axxess_auth_url
        self.client_id = settings.axxess_client_id
        self.client_secret = settings.axxess_client_secret
        self.account_id = settings.axxess_account_id
        self.time_zone = settings.axxess_time_zone

        # Token cache — avoids re-authenticating on every request
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    # ── Authentication ──────────────────────────────────────────────────────

    async def _fetch_token(self) -> str:
        """
        Request a new OAuth access token from Axxess identity server.
        Uses client_credentials grant (server-to-server, no user login needed).
        """
        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(
                self.auth_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "api",  # confirm exact scope with Axxess dev docs
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(f"Axxess auth failed: {response.text}")
                raise AxxessAuthError(
                    f"Failed to authenticate with Axxess: {response.status_code}"
                )

            data = response.json()
            self._access_token = data["access_token"]

            # Cache token with 60-second buffer before actual expiry
            expires_in = data.get("expires_in", 3600)
            self._token_expires_at = datetime.now() + timedelta(
                seconds=expires_in - 60
            )

            logger.info("Axxess access token refreshed successfully")
            return self._access_token

    async def _get_valid_token(self) -> str:
        """Return a cached token or fetch a new one if expired."""
        if (
            self._access_token is None
            or self._token_expires_at is None
            or datetime.now() >= self._token_expires_at
        ):
            return await self._fetch_token()
        return self._access_token

    def _build_headers(self) -> dict:
        """
        Build the standard headers required by every Axxess endpoint.
        NOTE: call _get_valid_token() before this to ensure token is fresh.
        """
        return {
            "Authorization": f"Bearer {self._access_token}",
            "X-Account-Id": self.account_id,
            "X-Time-Zone": self.time_zone,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ── Core HTTP Methods ───────────────────────────────────────────────────

    async def get(self, endpoint: str, params: dict = None) -> dict | list:
        """
        Make an authenticated GET request to the Axxess API.

        Args:
            endpoint: API path, e.g. "/api/v1/patients/{id}/slim"
            params:   Query parameters dict

        Returns:
            Parsed JSON response (dict or list)

        Raises:
            AxxessAPIError on non-2xx responses
        """
        await self._get_valid_token()
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.get(
                url,
                headers=self._build_headers(),
                params=params,
            )

        if response.status_code == 401:
            # Token may have expired mid-request — force refresh and retry once
            logger.warning("Got 401 from Axxess, refreshing token and retrying")
            await self._fetch_token()
            async with httpx.AsyncClient(timeout=30) as http:
                response = await http.get(
                    url,
                    headers=self._build_headers(),
                    params=params,
                )

        if not response.is_success:
            raise AxxessAPIError(response.status_code, response.text)

        return response.json()

    async def post(self, endpoint: str, body: dict) -> dict | list:
        """Make an authenticated POST request."""
        await self._get_valid_token()
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(
                url,
                headers=self._build_headers(),
                json=body,
            )

        if not response.is_success:
            raise AxxessAPIError(response.status_code, response.text)

        return response.json()

    # ── Patient Endpoints ───────────────────────────────────────────────────
    # Based on: 170.315(g)(7) and 170.315(g)(8) certified API documentation

    async def search_patients(
        self,
        term: str = None,
        date_of_birth: str = None,
        gender: int = None,
        patient_status: int = None,
    ) -> list[dict]:
        """
        Search patients by name, MRN, DOB, gender, or status.
        Endpoint: GET /api/v1/patients/patient-by-name-mrn

        Args:
            term:           FirstName, LastName, or MRN string
            date_of_birth:  ISO datetime string "YYYY-MM-DDTHH:MM:SS.sssZ"
            gender:         Enum int (get values from /api/v1/enums/Gender)
            patient_status: Enum int (get values from /api/v1/enums/PatientStatus)

        Returns:
            List of patient summary objects:
            [{ patientId, admissionId, branchId, firstName, lastName,
               middleInitial, medicalRecordNumber, dateOfBirth,
               status, lineOfService }]
        """
        params = {}
        if term:
            params["Term"] = term
        if date_of_birth:
            params["DateOfBirth"] = date_of_birth
        if gender is not None:
            params["Gender"] = gender
        if patient_status is not None:
            params["PatientStatus"] = patient_status

        return await self.get("/api/v1/patients/patient-by-name-mrn", params=params)

    async def get_patient(self, patient_id: str) -> dict:
        """
        Get full patient details by patient GUID.
        Endpoint: GET /api/v1/patients/{id}/slim

        Returns full patient object including:
        - Demographics (name, DOB, gender, address, lat/lng)
        - Insurance (Medicare #, Medicaid #, primary payer)
        - Clinical (diagnoses with ICD-10 codes, attending physician)
        - Episode info (admission date, benefit period, status)
        - Tags, authorizations flag, hospitalization status
        """
        return await self.get(f"/api/v1/patients/{patient_id}/slim")

    async def get_vitals(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
        page: int = 1,
        page_length: int = 50,
    ) -> dict:
        """
        Get vital signs for a patient within a date range.
        Endpoint: GET /api/v1/vitalsign

        Returns paginated vital sign records including:
        - Blood pressure (systolic/diastolic)
        - Temperature, respiration, oxygen saturation, pulse rate
        - Measurement metadata (position, route, method)
        """
        params = {
            "PatientId": patient_id,
            "StartDate": start_date,
            "EndDate": end_date,
            "Page": page,
            "PageLength": page_length,
        }
        return await self.get("/api/v1/vitalsign", params=params)

    async def get_care_plan(self, patient_id: str) -> list[dict]:
        """
        Get the patient's care plan — problems, goals, and interventions.
        Endpoint: GET /api/v1/poc/{patientId}

        Returns structured care plan areas with:
        - Problem statements
        - Associated goals (with responsible clinician)
        - Interventions by discipline
        """
        return await self.get(f"/api/v1/poc/{patient_id}")

    async def get_medications(
        self,
        patient_id: str,
        order: str = "asc",
        sort_by: str = "MedicationName",
    ) -> list[dict]:
        """
        Get all medications for a patient.
        Endpoint: GET /api/v1/medications

        Returns medication list including:
        - Drug name, dosage, route, frequency
        - Start/discontinue dates and ordering physicians
        - PRN flag, coverage status, related diagnosis
        """
        params = {
            "PatientId": patient_id,
            "Order": order,
            "SortBy": sort_by,
        }
        return await self.get("/api/v1/medications", params=params)

    async def get_allergies(
        self,
        patient_id: str,
        allergy_type: int = None,
    ) -> list[dict]:
        """
        Get patient allergies and adverse reactions.
        Endpoint: GET /api/v1/allergies

        Returns allergy records including:
        - Allergen name, reaction type, severity
        - Active/inactive status, start/end dates
        - Comments and information source
        """
        params = {"PatientId": patient_id}
        if allergy_type is not None:
            params["AllergyType"] = allergy_type
        return await self.get("/api/v1/allergies", params=params)

    async def get_ccda_summary(self, patient_id: str) -> str:
        """
        Get a full CCDA (C-CDA) clinical document summary for a patient.
        Endpoint: GET /api/v1/fhir/Patient/{id}/$cda-ccds

        Returns the complete clinical summary document including:
        - Allergies, encounters, immunizations
        - Medications, care plan, procedures
        - Lab results, vital signs, social history
        - Hospital discharge instructions

        Note: Returns XML/HTML formatted CCDA document.
        """
        await self._get_valid_token()
        url = f"{self.base_url}/api/v1/fhir/Patient/{patient_id}/$cda-ccds"

        async with httpx.AsyncClient(timeout=60) as http:
            response = await http.get(
                url,
                headers=self._build_headers(),
            )

        if not response.is_success:
            raise AxxessAPIError(response.status_code, response.text)

        return response.text  # CCDA is XML, not JSON

    # ── Convenience: Full Patient Profile ──────────────────────────────────

    async def get_full_patient_profile(self, patient_id: str) -> dict:
        """
        Pull a complete patient profile in one call by combining
        the core endpoints in parallel for speed.

        Returns a unified dict with all clinical context needed
        for the scheduling engine, documentation AI, and billing module.
        """
        import asyncio

        now = datetime.now()
        start_30 = (now - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00.000Z")
        end_now = now.strftime("%Y-%m-%dT23:59:59.000Z")

        # Run all requests concurrently — faster than sequential calls
        patient, care_plan, medications, allergies, vitals = await asyncio.gather(
            self.get_patient(patient_id),
            self.get_care_plan(patient_id),
            self.get_medications(patient_id),
            self.get_allergies(patient_id),
            self.get_vitals(patient_id, start_30, end_now),
        )

        return {
            "patient": patient,
            "care_plan": care_plan,
            "medications": medications,
            "allergies": allergies,
            "vitals": vitals,
            "pulled_at": now.isoformat(),
        }


# ── Singleton ───────────────────────────────────────────────────────────────
# One shared client instance across the app — token is cached internally
axxess = AxxessClient()
