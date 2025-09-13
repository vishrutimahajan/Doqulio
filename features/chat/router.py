from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
# Import schemas and the language map
from . import service, schemas

router = APIRouter()

@router.post("/chat", response_model=schemas.ChatResponse)
async def chat_endpoint(
    prompt: str = Form(...),
    # --- MODIFIED: Use the Language Enum for the parameter ---
    # This creates a dropdown in the API docs.
    target_language: schemas.Language | None = Form(None),
    file: UploadFile | None = File(None)
):
    """
    Handles chat interactions. The user can submit a text prompt with or without a file.
    """
    document_text = None
    file_data = None
    mime_type = None
    
    # --- ADDED: Convert the user-friendly language name to a two-letter code ---
    language_code = None
    if target_language:
        # Look up the code (e.g., "Hindi" -> "hi") from the map in schemas.py
        language_code = schemas.LANGUAGE_CODE_MAP.get(target_language)

    if file:
        allowed_mime_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # DOCX
            "image/png",
            "image/jpeg"
        ]
        if file.content_type not in allowed_mime_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Supported types are PDF, DOCX, PNG, JPEG."
            )

        mime_type = file.content_type
        file_data = await file.read()

        if file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            document_text = service.extract_text_from_file(file)
            file_data = None
            mime_type = None

    try:
        response_text = service.generate_chat_response(
            prompt=prompt,
            document_text=document_text,
            file_data=file_data,
            mime_type=mime_type,
            # Pass the two-letter language code to the service function
            target_language=language_code
        )
        return schemas.ChatResponse(response=response_text)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )