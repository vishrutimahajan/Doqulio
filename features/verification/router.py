# router.py

import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import StreamingResponse

# Import the service and schemas
from features.verification.service import verification_service
from features.verification.schemas import VerificationReport, ReportLanguage


# --- NEW: Mapping from full language name to ISO code ---
LANGUAGE_CODE_MAP = {
    "English": "en",
    "Hindi": "hi",
    "Bengali": "bn",
    "Marathi": "mr",
    "Telugu": "te",
    "Tamil": "ta",
    "Gujarati": "gu",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Punjabi": "pa",
}


router = APIRouter(
    prefix="/documents",
    tags=["Document Verification"]
)

@router.post(
    "/verify",
    summary="Verify a document and get a translated PDF report",
    description="Upload a document and select a regional language for the analysis report from the dropdown menu. "
)
async def verify_document_endpoint(
    file: UploadFile = File(..., description="The document file to be verified (PDF, JPG, PNG)."),
    description: str = Form(
        ..., 
        description="A short description of what the document is supposed to be (e.g., 'An invoice from ACME Corp')."
    ),
    # --- MODIFIED: The parameter now uses the Enum to create a dropdown ---
    output_language: ReportLanguage = Form(
        ReportLanguage.ENGLISH, # Default value
        description="Select the language for the final analysis report."
    ),
        user_id: str = Form(..., description="Firebase user ID for organizing docs in GCS")

):
    """
    Handles file upload, calls the verification service with a target language from the dropdown, and returns a PDF report.
        - Stores only the redacted file in GCS: docs/{user_id}/{filename}.txt
        - Returns the PDF report as a downloadable file.
        - Logs key events and errors for monitoring.
    """
    try:
        language_code = LANGUAGE_CODE_MAP[output_language.value]
        logging.info(
            f"Received request for document: {file.filename}. "
            f"User: {user_id}, Language: {output_language.value} ({language_code})"
        )

        file_content = await file.read()

        report_data: VerificationReport = verification_service.verify_document(
            file_content=file_content,
            filename=file.filename,
            description=description,
            output_language=language_code,
            user_id=user_id
        )
        pdf_buffer = verification_service.generate_pdf_report(report_data)
        
        safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ('.', '_')).rstrip()
        report_filename = f"verification_report_{language_code}_{safe_filename}.pdf"

        logging.info(f"Successfully generated '{language_code}' report for {file.filename}.")

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={report_filename}"}
        )

    except Exception as e:
        logging.error(f"An unexpected error occurred during document verification for {file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred while processing the document. Details: {str(e)}"
        )