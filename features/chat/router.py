"""
FastAPI Router for Chat Endpoints

This file defines the API routes for the chatbot functionality. It handles
incoming HTTP requests, validates them using Pydantic schemas, and uses the
chat service to generate responses.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional
from . import schemas, service

# Create an APIRouter instance
router = APIRouter(
    prefix="/chat",   # All routes will be under /chat
    tags=["Chatbot"]  # Group in API docs
)


@router.post(
    "/",
    response_model=schemas.ChatResponse,
    summary="Handle a chat conversation",
    description="""
    Sends a user message, conversation history, and optional file
    to the chatbot and gets a response.
    """
)
async def handle_chat_request(
    message: str = Form(..., description="The user's question or prompt for the chatbot."),
    history: Optional[str] = Form("[]", description="Conversation history in JSON format (optional)."),
    file: Optional[UploadFile] = File(None, description="Optional: Upload a document (PDF, DOCX, image) for context-aware answers.")
):
    """
    Main endpoint for chatbot interaction.

    - **Receives**: User's message, optional history, optional file
    - **Processes**:
        * Extracts text from file (if provided)
        * Calls the chatbot service with message + history + document context
    - **Returns**: Chatbot's reply and updated conversation history
    """
    document_text = None

    # Defensive: ignore empty string values
    if isinstance(file, str) and file.strip() == "":
        file = None

    # Extract document text if file provided
    if file is not None:
        try:
            document_text = service.extract_text_from_file(file)
            if not document_text or document_text.isspace():
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract text from the uploaded file. It might be empty or unreadable."
                )
        except HTTPException as e:
            raise e

    try:
        # Call the service to generate chatbot response
        response = service.generate_response(
            message=message,
            history=history,
            document_text=document_text
        )
        return response

    except Exception as e:
        print(f"Unhandled error in chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred on the server."
        )
