# Backend/ai/inspect_db.py
# Temporary script: queries the DB and prints a populated PatientDischargeContext as JSON.
# Run from the Backend folder:  python -m ai.inspect_db  OR  python ai/inspect_db.py

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Allow imports from the Backend folder when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.models import (
    PatientInformation,
    DischargeStatusInformation,
    Diagnosis,
    Procedure,
    HospitalizationEvent,
    PatientDischargeContext,
)

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

if not all([USER, PASSWORD, HOST, PORT, DBNAME]):
    raise ValueError("Missing DB env vars: user/password/host/port/dbname")


def get_connection():
    return psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME,
    )


def map_gender(value) -> str:
    """DimPatient.Gender is a boolean; map it to a readable string."""
    if value is True:
        return "Male"
    if value is False:
        return "Female"
    return "Unknown"


def fetch_patient(patient_id: int, cur) -> PatientInformation:
    cur.execute(
        """
        SELECT
            "PatientID",
            "FirstName",
            "MiddleName",
            "LastName",
            "Gender",
            "BirthDate",
            "Ethnicity",
            "Race"
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
        gender=map_gender(row["Gender"]),
        birth_date=row["BirthDate"],
        ethnicity=row["Ethnicity"],
        race=row["Race"],
    )


def fetch_hospitalizations(patient_id: int, cur) -> list[HospitalizationEvent]:
    # Pull all discharge events for the patient, joining to DimDate and DimDischargeStatus
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

        # ---- Diagnoses for this event ----
        cur.execute(
            """
            SELECT
                dx."DxCode",
                dx."DxName",
                dx."DxCategory"
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

        # ---- Procedures for this event ----
        cur.execute(
            """
            SELECT
                proc."ProcedureCode",
                proc."ProcedureName",
                proc."ProcedureCategory"
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

        discharge_status = DischargeStatusInformation(
            status_name=event["DischargeStatusName"],
            category=event["DischargeCategory"],
            is_deceased=event["IsDeceased"],
            is_transfer=event["IsTransfer"],
        )

        hospitalizations.append(
            HospitalizationEvent(
                event_id=event_id,
                admission_date=event["admission_date"],
                discharge_date=event["discharge_date"],
                length_of_stay=event["LOS"],
                discharge_status=discharge_status,
                diagnoses=diagnoses,
                procedures=procedures,
            )
        )

    return hospitalizations


def build_patient_context(patient_id: int) -> PatientDischargeContext:
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        patient = fetch_patient(patient_id, cur)
        hospitalizations = fetch_hospitalizations(patient_id, cur)

    return PatientDischargeContext(
        patient=patient,
        hospitalizations=hospitalizations,
    )


def peek_tables(limit: int = 5):
    """Print row counts and sample rows for every relevant table."""
    tables = [
        "DimPatient",
        "FactHospitalDischarge",
        "DimDischargeStatus",
        "FactPatientDx",
        "DimICDDx",
        "FactPatientProcedure",
        "DimICDProcedure",
    ]

    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        for table in tables:
            # row count
            cur.execute(f'SELECT COUNT(*) AS total FROM "{table}";')
            total = cur.fetchone()["total"]

            # sample rows
            cur.execute(f'SELECT * FROM "{table}" LIMIT %s;', (limit,))
            rows = cur.fetchall()

            print(f"\n{'='*60}")
            print(f"  {table}  ({total} total rows)")
            print(f"{'='*60}")
            if rows:
                # print column headers
                headers = list(rows[0].keys())
                print("  " + " | ".join(headers))
                print("  " + "-" * (len(" | ".join(headers)) + 2))
                for row in rows:
                    print("  " + " | ".join(str(v) for v in row.values()))
            else:
                print("  (no rows found)")


if __name__ == "__main__":
    for patient_id in [1, 2, 3]:
        print(f"\n{'='*60}")
        print(f"  PatientDischargeContext — PatientID={patient_id}")
        print(f"{'='*60}")
        try:
            context = build_patient_context(patient_id)
            print(context.model_dump_json(indent=2))
        except ValueError as e:
            print(f"  Skipped: {e}")