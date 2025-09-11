from enum import Enum
from pydantic import BaseModel, Field

class VerificationStatus(str, Enum):
    """Enumeration for the verification status of a document."""
    VERIFIED = "VERIFIED"
    SUSPICIOUS = "SUSPICIOUS"
    INDETERMINATE = "INDETERMINATE"
    ERROR = "ERROR"

class VerificationReport(BaseModel):
    """
    Represents the final report of a document verification process.
    Includes redacted text and a confidence score.
    """
    filename: str
    verification_status: VerificationStatus
    
    # --- NEW: Added confidence score with validation ---
    confidence_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="The AI's confidence in the verification status, from 0 to 100."
    )
    
    summary: str = Field(
        ...,
        description="A redacted one-sentence summary of the analysis findings."
    )
    
    analysis_details: str = Field(
        ...,
        description="A detailed, non-redacted explanation of the analysis reasoning."
    )
    
    extracted_text: str = Field(
        ...,
        description="The full, redacted text extracted from the document."
    )

    class Config:
        # This allows the model to be used with ORMs, if needed,
        # and provides example data for API documentation.
        from_attributes = True
        json_schema_extra = {
            "example": {
                "filename": "invoice_123.pdf",
                "verification_status": "SUSPICIOUS",
                "confidence_score": 85,
                "summary": "The document appears suspicious due to an inconsistent date format for user [REDACTED].",
                "analysis_details": "- The issue date '15-2024-05' does not follow a standard format.\n- The total amount seems unusually high for the items listed.",
                "extracted_text": "Invoice To: [REDACTED]\nAddress: [REDACTED]\nDate: 15-2024-05\nTotal: $5000.00"
            }
        }