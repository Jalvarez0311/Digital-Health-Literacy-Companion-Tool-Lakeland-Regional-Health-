"""Pydantic Models for the AI"""
from turtle import hideturtle
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
    name: str
    category: str


class Procedure(BaseModel):
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


# top level model
class PatientDischargeContext(BaseModel):
    patient: PatientInformation
    # hospitalizations sorted by discharge date DESC
    hospitalizations: List[HospitalizationEvent] = Field(default_factory=list)