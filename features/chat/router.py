"""
FastAPI Router for Chat Endpoints

This file defines the API routes for the chatbot functionality. It handles
incoming HTTP requests, validates them using Pydantic schemas, and uses the
chat service to generate responses.
"""
from fastapi import APIRouter, HTTPException, status
from . import schemas, service

# Create an APIRouter instance. This allows us to group related endpoints.
router = APIRouter(
    prefix="/chat",  # All routes in this file will be prefixed with /chat
    tags=["Chatbot"]  # Tag for organizing endpoints in the API docs
)

@router.post(
    "/",
    response_model=schemas.ChatResponse,
    summary="Handle a chat conversation",
    description="Sends a user message and conversation history to the chatbot and gets a response."
)
async def handle_chat_message(request: schemas.ChatRequest):
    """
    Main endpoint for chatbot interaction.

    - **Receives**: A JSON object containing the user's `message` and the
      conversation `history`.
    - **Processes**: Passes the message and history to the chat service, which
      interacts with the Gemini API.
    - **Returns**: A JSON object containing the chatbot's `reply` and the
      `updated_history`.
    """
    try:
        # Convert Pydantic ChatMessage objects in history to simple dicts
        # as expected by the service layer and Gemini API.
        history_dicts = [msg.model_dump() for msg in request.history]

        # Call the service function to get the response from the Gemini API
        response = service.generate_response(message=request.message, history=history_dicts)
        return response

    except Exception as e:
        # If any unexpected error occurs in the service layer,
        # return a generic 500 Internal Server Error.
        # In a production environment, you should log the error `e` for debugging.
        print(f"Unhandled error in chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred on the server."
        )
