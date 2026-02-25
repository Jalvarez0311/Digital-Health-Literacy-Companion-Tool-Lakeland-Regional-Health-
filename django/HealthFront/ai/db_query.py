"""builds a PatientDischargeContext from Supabase."""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from .models import (
    PatientInformation,
    DischargeStatusInformation,
    Diagnosis,
    Procedure,
    HospitalizationEvent,
    CurrentVisit,
    PatientDischargeContext,
)

load_dotenv()

USER   = os.getenv("user")
PASSWORD = os.getenv("password")
HOST   = os.getenv("host")
PORT   = os.getenv("port")
DBNAME = os.getenv("dbname")

if not all([USER, PASSWORD, HOST, PORT, DBNAME]):
    raise ValueError("Missing DB env vars: user / password / host / port / dbname")


def _get_connection():
    return psycopg2.connect(
        user=USER, password=PASSWORD, host=HOST, port=PORT, dbname=DBNAME
    )


def _map_gender(value) -> str:
    if value is True:
        return "Male"
    if value is False:
        return "Female"
    return "Unknown"


def _fetch_patient(patient_id: int, cur) -> PatientInformation:
    cur.execute(
        """
        SELECT
            "PatientID", "FirstName", "MiddleName", "LastName",
            "Gender", "BirthDate", "Ethnicity", "Race"
        FROM "DimPatient"
        WHERE "PatientID" = %s;
        """,
        (patient_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"No patient found with PatientID={patient_id}")

    return PatientInformation(
        patient_id=row["PatientID"],
        first_name=row["FirstName"] or "",
        middle_name=row["MiddleName"] or "",
        last_name=row["LastName"] or "",
        gender=_map_gender(row["Gender"]),
        birth_date=row["BirthDate"],
        ethnicity=row["Ethnicity"],
        race=row["Race"],
    )


def _fetch_hospitalizations(patient_id: int, cur) -> list[HospitalizationEvent]:
    cur.execute(
        """
        SELECT
            fhd."EventID",
            fhd."LOS",
            adm."Date"  AS admission_date,
            dis."Date"  AS discharge_date,
            dst."DischargeStatusName",
            dst."DischargeCategory",
            dst."IsDeceased",
            dst."IsTransfer"
        FROM "FactHospitalDischarge" fhd
        JOIN "DimDate" adm ON adm."DateID" = fhd."AdmissionDateID"
        JOIN "DimDate" dis ON dis."DateID" = fhd."DischargeDateID"
        JOIN "DimDischargeStatus" dst ON dst."DischargeStatusID" = fhd."DischargeStatusID"
        WHERE fhd."PatientID" = %s
        ORDER BY dis."Date" DESC;
        """,
        (patient_id,),
    )
    events = cur.fetchall()

    hospitalizations = []
    for event in events:
        event_id = event["EventID"]

        cur.execute(
            """
            SELECT dx."DxCode", dx."DxName", dx."DxCategory"
            FROM "FactPatientDx" fpd
            JOIN "DimICDDx" dx ON dx."DxID" = fpd."DxID"
            WHERE fpd."EventID" = %s;
            """,
            (event_id,),
        )
        diagnoses = [
            Diagnosis(
                code=row["DxCode"],
                name=row["DxName"] or "Unknown",
                category=row["DxCategory"] or "Unknown",
            )
            for row in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT proc."ProcedureCode", proc."ProcedureName", proc."ProcedureCategory"
            FROM "FactPatientProcedure" fpp
            JOIN "DimICDProcedure" proc ON proc."ProcedureID" = fpp."ProcedureID"
            WHERE fpp."EventID" = %s;
            """,
            (event_id,),
        )
        procedures = [
            Procedure(
                code=row["ProcedureCode"],
                name=row["ProcedureName"] or "Unknown",
                category=row["ProcedureCategory"] or "Unknown",
            )
            for row in cur.fetchall()
        ]

        hospitalizations.append(
            HospitalizationEvent(
                event_id=event_id,
                admission_date=event["admission_date"],
                discharge_date=event["discharge_date"],
                length_of_stay=event["LOS"],
                discharge_status=DischargeStatusInformation(
                    status_name=event["DischargeStatusName"],
                    category=event["DischargeCategory"],
                    is_deceased=event["IsDeceased"],
                    is_transfer=event["IsTransfer"],
                ),
                diagnoses=diagnoses,
                procedures=procedures,
            )
        )

    return hospitalizations


def fetch_patient_list() -> list[dict]:
    """Return [{id, name}] for every patient — used to populate the dropdown."""
    with _get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT "PatientID", "FirstName", "LastName"
            FROM "DimPatient"
            ORDER BY "LastName", "FirstName";
            """
        )
        return [
            {"id": row["PatientID"], "name": f"{row['FirstName']} {row['LastName']}"}
            for row in cur.fetchall()
        ]


def build_patient_context(patient_id: int, current_visit: CurrentVisit) -> PatientDischargeContext:
    """
    Query Supabase for a single patient and return a fully-populated
    PatientDischargeContext ready to be serialised and sent to the LLM.
    """
    with _get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        patient = _fetch_patient(patient_id, cur)
        hospitalizations = _fetch_hospitalizations(patient_id, cur)

    return PatientDischargeContext(
        patient=patient,
        current_visit=current_visit,
        hospitalizations=hospitalizations,
    )
