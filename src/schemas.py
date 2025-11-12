"""
Data schemas for healthcare workflow
"""

from typing import List
from pydantic import BaseModel, Field


class ClassificationSchema(BaseModel):
    """Schema for intent classification"""
    classification: str = Field(
        description="One of: government_scheme_support, mental_wellness_support, "
                    "ayush_support, symptom_checker, facility_locator_support"
    )
    reasoning: str = Field(description="Why this classification was chosen")


class SymptomCheckerSchema(BaseModel):
    """Schema for symptom information"""
    symptoms: List[str] = Field(description="List of symptoms")
    duration: str = Field(description="How long symptoms have persisted")
    severity: float = Field(description="Severity rating 0-10")
    age: float = Field(description="Patient age")
    comorbidities: List[str] = Field(description="Existing conditions", default_factory=list)
    triggers: str = Field(description="Symptom triggers if any", default="")
    additional_details: str = Field(description="Any other relevant info", default="")
    is_emergency: bool = Field(description="Whether this is an emergency")


class GovernmentSchemeSchema(BaseModel):
    """Schema for government scheme information"""
    scheme_name: str
    target_beneficiaries: str
    description: str
    official_link: str
