# router.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from . import service
from . import schemas

# Create a new router object
router = APIRouter(
    tags=["Chat"],
)

@router.post("/analyze-document", response_model=schemas.ChatResponse)
async def analyze_document_and_chat(
    file: UploadFile = File(..., description="The document to be analyzed (PDF, DOCX, or Image)."),
    prompt: str = Form(..., description="Your question or prompt about the document."),
    # This part remains the same, but will now generate a dropdown with full names
    lang: schemas.Language | None = Form(None, description="Select a language to translate the response.")
):
    """
    This endpoint analyzes an uploaded document and generates a response based on a user's prompt.
    
    - Supports **PDF**, **DOCX**, and **Image** files.
    - Optionally translates the AI's response into a specified language.
    """
    
    document_text: str | None = None
    file_data: bytes | None = None
    
    file_bytes = await file.read()
    
    content_type = file.content_type
    
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        document_text = service.extract_text_from_file(file)
    elif content_type == "application/pdf" or content_type.startswith("image/"):
        file_data = file_bytes
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {content_type}. Please upload a PDF, DOCX, or Image file."
        )

    # --- MODIFIED: Look up the language code from the map before calling the service ---
    target_language_code = None
    if lang:
        # Get the short code (e.g., "hi") from the selected enum member (e.g., Language.HINDI)
        target_language_code = schemas.LANGUAGE_CODE_MAP.get(lang)

    response_text = service.generate_chat_response(
        prompt=prompt,
        document_text=document_text,
        file_data=file_data,
        mime_type=content_type,
        target_language=target_language_code # Pass the correct short code
    )
    
    return schemas.ChatResponse(response=response_text)