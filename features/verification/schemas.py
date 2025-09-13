# schemas.py

from pydantic import BaseModel, Field
from enum import Enum

# --- NEW: Enum for user-friendly language selection ---
class ReportLanguage(str, Enum):
    """Enumeration for user-selectable report languages with full names."""
    ENGLISH = "English"
    HINDI = "Hindi"
    BENGALI = "Bengali"
    MARATHI = "Marathi"
    TELUGU = "Telugu"
    TAMIL = "Tamil"
    GUJARATI = "Gujarati"
    KANNADA = "Kannada"
    MALAYALAM = "Malayalam"
    PUNJABI = "Punjabi"
    
class VerificationStatus(str, Enum):
    """Enumeration for the verification status of a document."""
    VERIFIED = "VERIFIED"
    SUSPICIOUS = "SUSPICIOUS"
    INDETERMINATE = "INDETERMINATE"
    ERROR = "ERROR"

class VerificationReport(BaseModel):
    """
    Data model for the final verification report.
    """
    filename: str
    storage_url: str | None = Field(
        None, 
        description="URL of the uploaded document in Google Cloud Storage."
    )
    detected_language: str = Field(
        "en", 
        description="Language detected from the document's text (ISO 639-1 code)."
    )
    report_language: str = Field(
        "en",
        description="Language selected for the generated report analysis (ISO 639-1 code)."
    )
    verification_status: VerificationStatus
    confidence_score: int = Field(
        ..., 
        ge=0, 
        le=100, 
        description="The model's confidence in its verification status, from 0 to 100."
    )
    summary: str = Field(
        ..., 
        description="A concise, one-sentence summary of the verification findings in the report language."
    )
    analysis_details: str = Field(
        ..., 
        description="A detailed, bullet-pointed explanation of the findings in the report language."
    )
    extracted_text: str = Field(
        ..., 
        description="The full, redacted text extracted from the document."
    )