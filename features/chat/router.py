# router.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from . import schemas
from . import service
from google.generativeai import types   
router = APIRouter(
    prefix="/api",
    tags=["Chatbot"]
)

@router.post("/chat", response_model=schemas.ChatResponse)
async def handle_chat_request(
    prompt: str = Form(..., description="The user's question or prompt for the chatbot."),
    file: UploadFile | None = File(
        default=None,
        description="Optional: Upload a document (PDF, DOCX, image) for context-aware answers."
    )
):
    document_text = None
    file_data = None
    mime_type = None

    if file:
        mime_type = file.content_type
        # For DOCX, we still need to extract the text manually
        if mime_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
            try:
                document_text = service.extract_text_from_file(file)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process DOCX file: {str(e)}"
                )
        # For images and PDFs, we read the raw file data
        elif mime_type in ["image/jpeg", "image/png", "application/pdf"]:
            file_data = await file.read()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {mime_type}. Please upload a PDF, DOCX, or image file."
            )

        if not document_text and not file_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract any data from the uploaded file. It might be empty or unreadable."
            )

    try:
        answer = service.generate_chat_response(
            prompt=prompt,
            document_text=document_text,
            file_data=file_data,
            mime_type=mime_type
        )
        return schemas.ChatResponse(answer=answer)
    except HTTPException as e:
        raise e