from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from .schemas import VerificationReport
from .service import DocumentVerificationService, verification_service

router = APIRouter(
    prefix="/verify",
    tags=["📄 Document Verification"]
)

@router.post("/upload", response_model=VerificationReport)
async def upload_and_verify_document(
    description: str = Form(..., description="A short description of the document for accurate scanning and context."),
    file: UploadFile = File(..., description="The document file (e.g., PNG, JPG, PDF) to be verified."),
    service: DocumentVerificationService = Depends(lambda: verification_service)
):
    """
    Upload a document for verification.

    This endpoint performs two main actions:
    1.  **OCR Extraction**: Uses Google Cloud Vision to extract all text from the document.
    2.  **AI Analysis**: Sends the extracted text to Gemini for fraud and tampering analysis.

    Returns a detailed JSON verification report.
    """
    # Supported content types
    SUPPORTED_CONTENT_TYPES = ["image/jpeg", "image/png", "application/pdf", "image/tiff"]
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Please upload a valid image or PDF file. Supported types are: {', '.join(SUPPORTED_CONTENT_TYPES)}"
        )
        
    try:
        file_content = await file.read()
        report = service.verify_document(
            file_content=file_content,
            filename=file.filename,
            description=description
        )
        return report
    except Exception as e:
        # Catch-all for any unexpected errors during processing
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

@router.post("/download-report", response_class=PlainTextResponse)
async def download_verification_report(report: VerificationReport):
    """
    Generates a downloadable plain text file from a verification report JSON.

    Your frontend should first call the `/upload` endpoint to get the report JSON,
    then send that same JSON to this endpoint to receive the downloadable .txt file.
    """
    report_content = f"""
=========================================
   DOCUMENT VERIFICATION REPORT
=========================================

Report ID:      {report.report_id}
Filename:       {report.filename}
Verified At:    {report.verified_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Status:         {report.verification_status.value}

-----------------------------------------
              SUMMARY
-----------------------------------------
{report.summary}

-----------------------------------------
          AI ANALYSIS DETAILS
-----------------------------------------
{report.analysis_details}

-----------------------------------------
        EXTRACTED DOCUMENT TEXT
-----------------------------------------
{report.extracted_text}

=========================================
       END OF REPORT
=========================================
"""
    # The browser will be prompted to download this response as a file
    return PlainTextResponse(
        content=report_content,
        headers={
            "Content-Disposition": f"attachment; filename=verification_report_{report.filename}.txt"
        }
    )