import uuid
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class VerificationStatus(str, Enum):
    """
    Enumeration for the verification status of a document.
    """
    VERIFIED = "✅ Verified"
    SUSPICIOUS = "⚠️ Suspicious"
    ERROR = "❌ Error"
    INDETERMINATE = "🤔 Indeterminate"

class VerificationReport(BaseModel):
    """
    Represents the detailed verification report generated for a document.
    """
    report_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    filename: str
    verification_status: VerificationStatus
    summary: str = Field(..., description="A concise summary of the verification findings.")
    analysis_details: str = Field(..., description="Detailed analysis from the AI model regarding tampering or suspicious content.")
    extracted_text: str = Field(description="The full text extracted from the document by OCR.")
    verified_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        # Allows the model to be created from ORM objects (not used here, but good practice)
        orm_mode = True
        # Provides example data for API documentation (e.g., in Swagger UI)
        schema_extra = {
            "example": {
                "report_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                "filename": "invoice_123.pdf",
                "verification_status": "⚠️ Suspicious",
                "summary": "The document shows signs of potential alteration. The total amount appears inconsistent with the itemized list.",
                "analysis_details": "Gemini Analysis:\n- Mismatch found between the sum of line items ($450.00) and the stated total amount ($550.00).\n- The font used for the total amount differs slightly from the rest of the document, suggesting a possible modification.\n- No other signs of tampering were detected.",
                "extracted_text": "Invoice #123...\nItem 1: $200\nItem 2: $250\nTotal: $550...",
                "verified_at": "2025-09-07T12:00:00Z"
            }
        }