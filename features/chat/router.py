# router.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from . import schemas
from . import service

# Create an API router
router = APIRouter(
    prefix="/api",
    tags=["Chatbot"]
)

@router.post("/chat", response_model=schemas.ChatResponse)
async def handle_chat_request(
    prompt: str = Form(
        ...,
        description="The user's question or prompt for the chatbot."
    ),
    file: UploadFile | None = File(
        default=None,
        description="Optional: Upload a document (PDF, DOCX, image) for context-aware answers."
    )
):
    """
    This endpoint powers the Doqulio chatbot.

    It can handle two types of requests:
    1.  **General Question:** Provide a `prompt` without a `file`.
    2.  **Document-based Question:** Provide both a `prompt` and a `file`. The chatbot will use the file's content as a reference to answer the prompt.
    """
    document_text = None

    # Step 1: If a file is uploaded, extract its text content
    if file:
        try:
            document_text = service.extract_text_from_file(file)
            if not document_text or document_text.isspace():
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract any text from the uploaded file. It might be empty or unreadable."
                )
        except HTTPException as e:
            # Re-raise exceptions from the service layer to the client
            raise e

    # Step 2: Generate a response using the prompt and the (optional) extracted text
    try:
        answer = service.generate_chat_response(prompt=prompt, document_text=document_text)
        return schemas.ChatResponse(answer=answer)
    except HTTPException as e:
        # Re-raise exceptions from the service layer to the client
        raise e