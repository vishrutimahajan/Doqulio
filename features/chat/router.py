# router.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from . import schemas
from . import service

# Create an API router
router = APIRouter(
    prefix="/api",
    tags=["Chatbot"]
)

# ...existing code...

@router.post("/chat", response_model=schemas.ChatResponse)
async def handle_chat_request(
    prompt: str = Form(
        ...,
        description="The user's question or prompt for the chatbot."
    ),
    file: UploadFile = File(
        default=None,
        description="Optional: Upload a document (PDF, DOCX, image) for context-aware answers."
    )
):
    document_text = None

    # Defensive: Ignore empty string file values
    if isinstance(file, str) and file == "":
        file = None

    if file is not None:
        try:
            document_text = service.extract_text_from_file(file)
            if not document_text or document_text.isspace():
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract any text from the uploaded file. It might be empty or unreadable."
                )
        except HTTPException as e:
            raise e

    try:
        answer = service.generate_chat_response(prompt=prompt, document_text=document_text)
        return schemas.ChatResponse(answer=answer)
    except HTTPException as e:
        raise e