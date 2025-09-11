from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import StreamingResponse

from .schemas import VerificationReport
from .service import verification_service # Import the service instance

# Create a new router
router = APIRouter(
    prefix="/documents",
    tags=["Document Verification"]
)

@router.post("/verify", response_model=VerificationReport)
async def verify_document_endpoint(
    file: UploadFile = File(..., description="The document (image or PDF) to verify."),
    description: str = Form(..., description="A brief description of what the document is (e.g., 'This is a rental agreement from May').")
):
    """
    Verifies a document by analyzing its text content and returns a JSON report.
    """
    supported_types = ["image/jpeg", "image/png", "application/pdf"]
    if file.content_type not in supported_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Please upload a JPEG, PNG, or PDF."
        )
    
    try:
        file_content = await file.read()
        report = verification_service.verify_document(
            file_content=file_content,
            filename=file.filename,
            description=description
        )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

# --- NEW: Endpoint to generate and download a PDF report ---
@router.post("/download-report", response_class=StreamingResponse)
async def download_report_endpoint(report: VerificationReport):
    """
    Generates a downloadable PDF report from a verification result.

    **How to use:**
    1. First, get a successful JSON response from the `/verify` endpoint.
    2. Then, send that entire JSON object as the body of this request.
    """
    try:
        # Generate the PDF using the service
        pdf_buffer = verification_service.generate_pdf_report(report)
        
        # Create headers to prompt a download
        headers = {
            'Content-Disposition': f'attachment; filename="verification_report_{report.filename}.pdf"'
        }
        
        # Stream the PDF back to the client
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}"
        )