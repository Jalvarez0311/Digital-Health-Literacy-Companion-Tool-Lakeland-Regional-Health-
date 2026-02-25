"""Pydantic Models for the AI"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class PatientInformation(BaseModel):
    patient_id: int
    first_name: str
    middle_name: str
    last_name: str
    gender: str
    birth_date: Optional[date] = None
    ethnicity: Optional[str] = None
    race: Optional[str] = None


class DischargeStatusInformation(BaseModel):
    status_name: str
    category: Optional[str] = None
    is_deceased: bool
    is_transfer: bool


class Diagnosis(BaseModel):
    code: Optional[str] = None
    name: str
    category: str


class Procedure(BaseModel):
    code: Optional[str] = None
    name: str
    category: str


class HospitalizationEvent(BaseModel):
    event_id: int
    admission_date: date
    discharge_date: date
    length_of_stay: Optional[int] = None
    # hospital_branch:
    # admission_source
    # admission_type
    discharge_status: Optional[DischargeStatusInformation] = None
    diagnoses: List[Diagnosis] = Field(default_factory=list)
    procedures: List[Procedure] = Field(default_factory=list)


class CurrentVisit(BaseModel):
    visit_date: date
    reason_for_visit: str
    current_diagnoses: List[str] = Field(default_factory=list)
    current_medications: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


# top level model
class PatientDischargeContext(BaseModel):
    patient: PatientInformation
    current_visit: CurrentVisit
    # hospitalizations sorted by discharge date DESC
    hospitalizations: List[HospitalizationEvent] = Field(default_factory=list)