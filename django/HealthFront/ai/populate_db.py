# Backend/ai/populate_db.py
# Seeds all empty dimension tables, then generates 0-4 hospitalization
# events for the first 3 patients.
# Run from the Backend folder:  python ai/populate_db.py

import os
import sys
import random
import calendar
from datetime import date, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
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
        user=USER, password=PASSWORD, host=HOST, port=PORT, dbname=DBNAME
    )


# date dimension helper functions (ty AI)
def _day_suffix(day: int) -> str:
    if 11 <= day <= 13:
        return f"{day}th"
    return f"{day}{['th','st','nd','rd','th','th','th','th','th','th'][day % 10]}"

def _week_of_month(d: date) -> int:
    return (d.day + d.replace(day=1).weekday()) // 7 + 1


def _has_53_iso_weeks(year: int) -> int:
    return 1 if date(year, 12, 28).isocalendar()[0] == year else 0


def _quarter_bounds(year: int, quarter: int):
    starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
    ends   = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    qs, qe = starts[quarter], ends[quarter]
    return date(year, *qs), date(year, *qe)


def seed_dim_date(cur, start_year: int = 2020, end_year: int = 2026):
    cur.execute('SELECT COUNT(*) AS cnt FROM "DimDate";')
    if cur.fetchone()["cnt"] > 0:
        print("  DimDate: already populated, skipping.")
        return


    rows = []
    date_id = 1
    d = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    while d <= end:
        iso_year, iso_week, _ = d.isocalendar()
        quarter = (d.month - 1) // 3 + 1
        first_of_month  = d.replace(day=1)
        last_of_month   = d.replace(day=calendar.monthrange(d.year, d.month)[1])
        next_month      = (d.month % 12) + 1
        next_month_year = d.year + (1 if d.month == 12 else 0)
        first_of_next   = date(next_month_year, next_month, 1)
        last_of_next    = first_of_next.replace(
            day=calendar.monthrange(next_month_year, next_month)[1]
        )
        qstart, qend = _quarter_bounds(d.year, quarter)
        monday = d - timedelta(days=d.weekday())

        rows.append((
            d, d.day, _day_suffix(d.day), d.strftime("%A"),
            d.weekday() + 1,                       # DayOfWeek 1=Mon
            _week_of_month(d),                     # DayOfWeekInMonth
            d.timetuple().tm_yday,                 # DayOfYear
            1 if d.weekday() >= 5 else 0,          # IsWeekend
            iso_week, iso_week,                    # Week, ISOWeek
            monday, monday + timedelta(days=6),    # FirstOfWeek, LastOfWeek
            _week_of_month(d),                     # WeekOfMonth
            d.month, d.strftime("%B"),
            first_of_month, last_of_month,
            first_of_next, last_of_next,
            quarter, qstart, qend,
            d.year, iso_year,
            date(d.year, 1, 1), date(d.year, 12, 31),
            1 if calendar.isleap(d.year) else 0,
            1 if date(d.year, 1, 1).weekday() == 3 else 0,  # Has53Weeks (approx)
            _has_53_iso_weeks(d.year),
            d.strftime("%m%Y"),
            d.strftime("%m/%d/%Y"),
            d.strftime("%d/%m/%Y"),
            d.strftime("%Y%m%d"),
            d.strftime("%Y-%m-%d"),
            date_id,
        ))
        date_id += 1
        d += timedelta(days=1)

    cur.executemany(
        """
        INSERT INTO "DimDate" (
            "Date","Day","DaySuffix","DayName","DayOfWeek",
            "DayOfWeekInMonth","DayOfYear","IsWeekend",
            "Week","ISOWeek","FirstOfWeek","LastOfWeek","WeekOfMonth",
            "Month","MonthName","FirstOfMonth","LastOfMonth",
            "FirstOfNextMonth","LastOfNextMonth",
            "Quarter","FirstOfQuarter","LastOfQuarter",
            "Year","ISOYear","FirstOfYear","LastOfYear",
            "IsLeapYear","Has53Weeks","Has53ISOWeeks",
            "mmyyyy","style101","style103","style112","style120",
            "DateID"
        ) VALUES (
            %s,%s,%s,%s,%s,
            %s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,
            %s,%s,
            %s,%s,%s,
            %s,%s,%s,%s,
            %s,%s,%s,
            %s,%s,%s,%s,%s,
            %s
        )
        """,
        rows,
    )
    print(f"  DimDate: inserted {len(rows)} rows ({start_year}–{end_year})")


def seed_dim_discharge_status(cur):
    cur.execute('SELECT COUNT(*) AS cnt FROM "DimDischargeStatus";')
    if cur.fetchone()["cnt"] > 0:
        print("  DimDischargeStatus: already populated, skipping.")
        return

    statuses = [
        # lowkey idk if this is correct but it seems viable. very changable.
        (1, "01", 1,  "Discharged to Home",                   "Routine",   False, False, False),
        (2, "02", 2,  "Discharged to Skilled Nursing Facility","Post-Acute",False, False, False),
        (3, "03", 3,  "Discharged to Inpatient Rehab",         "Post-Acute",False, False, False),
        (4, "06", 6,  "Discharged to Home Health Care",        "Routine",   False, False, False),
        (5, "07", 7,  "Left Against Medical Advice",           "AMA",       False, False, True),
        (6, "20", 20, "Expired",                               "Deceased",  True,  False, False),
        (7, "30", 30, "Transfer to Another Hospital",          "Transfer",  False, True,  False),
        (8, "50", 50, "Hospice Home",                        "Hospice",   False, False, False),
    ]
    cur.executemany(
        """
        INSERT INTO "DimDischargeStatus"
            ("DischargeStatusID","DischargeStatusCode","NUBCCode",
             "DischargeStatusName","DischargeCategory",
             "IsDeceased","IsTransfer","IsAMAFlag")
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        statuses,
    )
    print(f"  DimDischargeStatus: inserted {len(statuses)} rows")


def seed_dim_admission_source(cur):
    # single placeholder row - column is NOT NULL so a value is required.
    cur.execute('SELECT COUNT(*) AS cnt FROM "DimAdmissionSource";')
    if cur.fetchone()["cnt"] > 0:
        print("  DimAdmissionSource: already populated, skipping.")
        return
    cur.execute(
        'INSERT INTO "DimAdmissionSource" ("AdmissionSourceID","SourceName","SourceCategoryID") VALUES (%s,%s,%s)',
        (1, "N/A", 1),
    )
    print("  DimAdmissionSource: inserted 1 placeholder row (NOT NULL requirement)")


def seed_dim_admission_type(cur):
    # single placeholder row - column is NOT NULL so a value is required.
    cur.execute('SELECT COUNT(*) AS cnt FROM "DimAdmissionType";')
    if cur.fetchone()["cnt"] > 0:
        print("  DimAdmissionType: already populated, skipping.")
        return
    cur.execute(
        'INSERT INTO "DimAdmissionType" ("AdmissionTypeID","Description","AdmissionCategory") VALUES (%s,%s,%s)',
        (1, "N/A", 1),
    )
    print("  DimAdmissionType: inserted 1 placeholder row (NOT NULL requirement)")


def seed_dim_hospital_branch(cur):
    # single row for Lakeland Regional Health - column is NOT NULL so a value is required.
    cur.execute('SELECT COUNT(*) AS cnt FROM "DimHospitalBranch";')
    if cur.fetchone()["cnt"] > 0:
        print("  DimHospitalBranch: already populated, skipping.")
        return
    cur.execute(
        """
        INSERT INTO "DimHospitalBranch"
            ("HospitalBranchID","Name","Address","County","City","ZipCode","Beds","YearFounded")
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (1, "Lakeland Regional Health Medical Center", "1324 Lakeland Hills Blvd", "Polk", "Lakeland", 33805, 531, 1916),
    )
    print("  DimHospitalBranch: inserted 1 row (Lakeland Regional Health)")


# fact table helper functions 

def get_date_id(cur, d: date) -> int:
    cur.execute('SELECT "DateID" FROM "DimDate" WHERE "Date" = %s;', (d,))
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"Date {d} not found in DimDate. Is DimDate seeded?")
    return row["DateID"]


def next_event_id(cur) -> int:
    cur.execute('SELECT COALESCE(MAX("EventID"), 0) + 1 AS nxt FROM "FactHospitalDischarge";')
    return cur.fetchone()["nxt"]


def next_patient_dx_id(cur) -> int:
    cur.execute('SELECT COALESCE(MAX("PatientDxID"), 0) + 1 AS nxt FROM "FactPatientDx";')
    return cur.fetchone()["nxt"]


def next_patient_proc_id(cur) -> int:
    cur.execute('SELECT COALESCE(MAX("PatientProcedureID"), 0) + 1 AS nxt FROM "FactPatientProcedure";')
    return cur.fetchone()["nxt"]


# clinical scenario bundles (made by AI, we can't just randomly populate multiple scenarios)
# discharge_status_id maps to DimDischargeStatus:
# 1=Home  2=SNF  3=Rehab  4=Home Health  5=AMA  6=Expired  7=Transfer

CLINICAL_SCENARIOS = [
    {
        "name": "Acute Nasopharyngitis (Common Cold)",
        "dx_codes": ["CA00"],
        "proc_codes": ["XG2XJ6"],
        "discharge_status_id": 1,
        "los_range": (1, 2),
    },
    {
        "name": "Allergic Rhinitis Exacerbation",
        "dx_codes": ["CA08.00"],
        "proc_codes": ["XG2XJ6", "XG1Y88"],
        "discharge_status_id": 1,
        "los_range": (1, 2),
    },
    {
        "name": "Acute Pharyngitis",
        "dx_codes": ["CA02.0"],
        "proc_codes": ["XG2XJ6", "XG4D55"],
        "discharge_status_id": 1,
        "los_range": (1, 2),
    },
    {
        "name": "Acute Bronchitis",
        "dx_codes": ["CA20.0"],
        "proc_codes": ["XG2XJ6", "PZA.DD.AC"],
        "discharge_status_id": 1,
        "los_range": (2, 3),
    },
    {
        "name": "Viral Gastroenteritis",
        "dx_codes": ["1A40.0"],
        "proc_codes": ["XG2XJ6", "XG1Y88", "XG2VK6"],
        "discharge_status_id": 1,
        "los_range": (2, 3),
    },
    {
        "name": "Mild Dehydration",
        "dx_codes": ["5C70.0"],
        "proc_codes": ["XG1Y88", "XG2VK6"],
        "discharge_status_id": 1,
        "los_range": (1, 2),
    },
    {
        "name": "Uncomplicated UTI / Cystitis",
        "dx_codes": ["GC00.1"],
        "proc_codes": ["XG4F04", "XG79M8"],
        "discharge_status_id": 1,
        "los_range": (2, 3),
    },
    {
        "name": "Low Back Pain",
        "dx_codes": ["ME84.2Z", "ME84.3"],
        "proc_codes": ["XG2XJ6", "XG2VK6"],
        "discharge_status_id": 1,
        "los_range": (2, 4),
    },
    {
        "name": "Asthma Exacerbation",
        "dx_codes": ["CA23.00"],
        "proc_codes": ["XG2XJ6", "PZA.DD.AC", "HTB.AC.AH"],
        "discharge_status_id": 1,
        "los_range": (3, 5),
    },
    {
        "name": "Hypertensive Urgency",
        "dx_codes": ["BA00.0"],
        "proc_codes": ["HTB.AC.AH", "XG2VK6", "XG94P6"],
        "discharge_status_id": 1,
        "los_range": (2, 3),
    },
    {
        "name": "Type 2 Diabetes with Hyperglycaemia",
        "dx_codes": ["5A11", "5A24"],
        "proc_codes": ["XG4N58", "XG2VK6", "XG9LX4"],
        "discharge_status_id": 1,
        "los_range": (3, 5),
    },
    {
        "name": "COPD with Acute Exacerbation",
        "dx_codes": ["CA22.0", "CA20.1Z"],
        "proc_codes": ["XG2XJ6", "PZA.DD.AC", "XG8DL0"],
        "discharge_status_id": 1,
        "los_range": (4, 7),
    },
    {
        "name": "Community-Acquired Pneumonia",
        "dx_codes": ["CA40.07", "BA00.0"],
        "proc_codes": ["XG2XJ6", "XG4D55", "XG8DL0", "PZA.DD.AC"],
        "discharge_status_id": 1,
        "los_range": (4, 7),
    },
    {
        "name": "Pyelonephritis with Sepsis",
        "dx_codes": ["GC00.1", "1G40"],
        "proc_codes": ["XG4D55", "XG2XJ6", "XG94P6", "XG79M8"],
        "discharge_status_id": 1,
        "los_range": (4, 7),
    },
    {
        "name": "Bacterial Cellulitis",
        "dx_codes": ["1B70.Z", "5A11"],
        "proc_codes": ["XG2XJ6", "XG4D55"],
        "discharge_status_id": 1,
        "los_range": (4, 6),
    },
    {
        "name": "New-Onset Atrial Fibrillation",
        "dx_codes": ["BC81.30", "BA00.0"],
        "proc_codes": ["HTB.AC.AH", "XG2XJ6", "XG7EG0", "XG2VK6"],
        "discharge_status_id": 1,
        "los_range": (3, 5),
    },
    {
        "name": "Deep Vein Thrombosis",
        "dx_codes": ["BD71.4", "BA00.0"],
        "proc_codes": ["XG2XJ6", "DTA.DB.AE"],
        "discharge_status_id": 1,
        "los_range": (3, 5),
    },
    {
        "name": "Acute Kidney Injury Stage 1",
        "dx_codes": ["GB60.0", "5A11", "BA00.0"],
        "proc_codes": ["XG94P6", "XG7ZG3", "XG2VK6", "XG1Y88"],
        "discharge_status_id": 1,
        "los_range": (3, 6),
    },
    {
        "name": "Acute Appendicitis",
        "dx_codes": ["DB10.02", "1G40"],
        "proc_codes": ["XG2XJ6", "KBO.JK.AB", "XG4D55"],
        "discharge_status_id": 1,
        "los_range": (2, 4),
    },
    {
        "name": "Pulmonary Embolism",
        "dx_codes": ["BD71.4", "BB01.3"],
        "proc_codes": ["XG2XJ6", "XG8DL0", "DTA.DB.AE", "HID.DB.AF"],
        "discharge_status_id": 1,
        "los_range": (5, 7),
    },
    {
        "name": "Congestive Heart Failure Exacerbation",
        "dx_codes": ["BD10", "BA00.0", "BC81.31"],
        "proc_codes": ["HTB.AC.AH", "XG2XJ6", "XG2VK6", "XG7EG0", "PZA.DD.AC"],
        "discharge_status_id": 4,  # Home Health Care
        "los_range": (5, 7),
    },
    {
        "name": "Severe COPD with Respiratory Failure",
        "dx_codes": ["CA22.0", "CA21.2"],
        "proc_codes": ["PZA.DD.AC", "XG8DL0", "XG2XJ6", "HTB.AC.AH"],
        "discharge_status_id": 2,  # SNF
        "los_range": (7, 10),
    },
    {
        "name": "Sepsis without Septic Shock (UTI source)",
        "dx_codes": ["1G40", "GC00.1"],
        "proc_codes": ["XG4D55", "XG2XJ6", "XG37U7", "XG9LX4"],
        "discharge_status_id": 1,
        "los_range": (5, 8),
    },
    {
        "name": "Sepsis with Septic Shock (Pneumonia source)",
        "dx_codes": ["1G41", "CA40.07"],
        "proc_codes": ["XG4D55", "XG2XJ6", "XG37U7", "XG8DL0", "NAA.JC.AF"],
        "discharge_status_id": 2,  # SNF
        "los_range": (8, 14),
    },
    {
        "name": "Non-ST Elevation MI (NSTEMI)",
        "dx_codes": ["BA41.1", "BA00.0", "BC81.3Z"],
        "proc_codes": ["HTB.AC.AH", "XG7EG0", "XG2VK6", "HIA.BA.BB"],
        "discharge_status_id": 1,
        "los_range": (4, 6),
    },
    {
        "name": "ST-Elevation MI (STEMI)",
        "dx_codes": ["BA41.0", "BA00.0", "5A11"],
        "proc_codes": ["HTB.AC.AH", "XG7EG0", "HIA.BA.BB", "HIA.DB.AF", "XG9LX4"],
        "discharge_status_id": 3,  # Rehab
        "los_range": (5, 8),
    },
    {
        "name": "Acute Kidney Failure Stage 3 with Dialysis",
        "dx_codes": ["GB60.2", "5A11", "BA00.0"],
        "proc_codes": ["XG94P6", "XG7ZG3", "XG1Y88", "NAA.JC.AF"],
        "discharge_status_id": 2,  # SNF
        "los_range": (10, 14),
    },
    {
        "name": "Hip Fracture with Replacement",
        "dx_codes": ["NC72.2Z", "BA00.0"],
        "proc_codes": ["MLJ.KA.AA", "XG2XJ6", "XG0F85"],
        "discharge_status_id": 3,  # Rehab
        "los_range": (5, 8),
    },
    {
        "name": "Ischaemic Stroke",
        "dx_codes": ["8B11.0", "BA00.0", "BC81.31"],
        "proc_codes": ["IAA.BA.BC", "HTB.AC.AH", "XG2XJ6", "IAA.DB.AF"],
        "discharge_status_id": 3,  # Rehab
        "los_range": (7, 14),
    },
    {
        "name": "Intracerebral Haemorrhage",
        "dx_codes": ["8B00.Z", "BA00.0", "BC81.31"],
        "proc_codes": ["IAA.BA.BH", "IAA.BA.BC", "XG2XJ6", "HTB.AC.AH"],
        "discharge_status_id": 3,  # Rehab
        "los_range": (10, 14),
    },
]



def build_code_lookups(cur) -> tuple[dict, dict]:
    """Return (dx_code -> DxID, proc_code -> ProcedureID) dicts."""
    cur.execute('SELECT "DxID", "DxCode" FROM "DimICDDx" WHERE "DxCode" IS NOT NULL;')
    dx_lookup = {r["DxCode"]: r["DxID"] for r in cur.fetchall()}

    cur.execute('SELECT "ProcedureID", "ProcedureCode" FROM "DimICDProcedure" WHERE "ProcedureCode" IS NOT NULL;')
    proc_lookup = {r["ProcedureCode"]: r["ProcedureID"] for r in cur.fetchall()}

    return dx_lookup, proc_lookup


def seed_events_for_patients(cur, patient_limit: int = 3):
    BRANCH_ID = 1
    SOURCE_ID = 1
    TYPE_ID   = 1

    print("  Building code lookup tables...")
    dx_lookup, proc_lookup = build_code_lookups(cur)

    all_dx_codes   = {c for s in CLINICAL_SCENARIOS for c in s["dx_codes"]}
    all_proc_codes = {c for s in CLINICAL_SCENARIOS for c in s["proc_codes"]}
    missing_dx   = all_dx_codes   - dx_lookup.keys()
    missing_proc = all_proc_codes - proc_lookup.keys()
    if missing_dx:
        print(f"  WARNING: Dx codes not found in DB: {missing_dx}")
    if missing_proc:
        print(f"  WARNING: Procedure codes not found in DB: {missing_proc}")

    # fetch the first N patients
    cur.execute(
        'SELECT "PatientID", "FirstName", "LastName" FROM "DimPatient" ORDER BY "PatientID" LIMIT %s;',
        (patient_limit,),
    )
    patients = cur.fetchall()

    total_events = 0

    for patient in patients:
        pid = patient["PatientID"]
        name = f"{patient['FirstName']} {patient['LastName']}"
        num_events = random.randint(0, 4)
        print(f"\n  Patient {pid} ({name}): generating {num_events} event(s)")

        for _ in range(num_events):
            scenario = random.choice(CLINICAL_SCENARIOS)
            los_min, los_max = scenario["los_range"]
            los = random.randint(los_min, los_max)

            year = random.randint(2022, 2025)
            month = random.randint(1, 12)
            max_day = calendar.monthrange(year, month)[1]
            admission = date(year, month, random.randint(1, max_day - 3))
            discharge = admission + timedelta(days=los)
            if discharge.year > 2026:
                discharge = date(2026, 12, 1)

            adm_date_id = get_date_id(cur, admission)
            dis_date_id = get_date_id(cur, discharge)
            event_id    = next_event_id(cur)

            cur.execute(
                """
                INSERT INTO "FactHospitalDischarge" (
                    "EventID","HospitalBranchID","PatientID",
                    "AdmissionDateID","DischargeDateID",
                    "AdmissionSourceID","AdmissionTypeID","DischargeStatusID",
                    "LOS"
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    event_id, BRANCH_ID, pid,
                    adm_date_id, dis_date_id,
                    SOURCE_ID, TYPE_ID,
                    scenario["discharge_status_id"],
                    los,
                ),
            )

            # diagnoses from scenario codes
            dx_id_counter = next_patient_dx_id(cur)
            inserted_dx = 0
            for code in scenario["dx_codes"]:
                db_id = dx_lookup.get(code)
                if db_id is None:
                    continue
                cur.execute(
                    'INSERT INTO "FactPatientDx" ("PatientDxID","EventID","DxID") VALUES (%s,%s,%s)',
                    (dx_id_counter, event_id, db_id),
                )
                dx_id_counter += 1
                inserted_dx += 1

            # procedures from scenario codes
            proc_id_counter = next_patient_proc_id(cur)
            inserted_proc = 0
            for code in scenario["proc_codes"]:
                db_id = proc_lookup.get(code)
                if db_id is None:
                    continue
                cur.execute(
                    'INSERT INTO "FactPatientProcedure" ("PatientProcedureID","EventID","ProcedureID") VALUES (%s,%s,%s)',
                    (proc_id_counter, event_id, db_id),
                )
                proc_id_counter += 1
                inserted_proc += 1

            print(
                f"    EventID {event_id}: [{scenario['name']}] "
                f"{admission} → {discharge} "
                f"(LOS={los}d, Dx={inserted_dx}, Proc={inserted_proc})"
            )
            total_events += 1

    print(f"\n  Total events inserted: {total_events}")


with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
    seed_dim_date(cur)
    seed_dim_discharge_status(cur)
    seed_dim_admission_source(cur)
    seed_dim_admission_type(cur)
    seed_dim_hospital_branch(cur)
    conn.commit()
    print("\n=== Generating hospitalization events for first 1 patient (test) ===")
    seed_events_for_patients(cur, patient_limit=100)
    conn.commit()
print("\nDone. Run inspect_db.py to verify the data.")

