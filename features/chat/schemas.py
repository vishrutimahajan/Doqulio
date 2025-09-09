"""
Pydantic Schemas for Chatbot API

This file defines the data structures for the API request and response bodies.
Using Pydantic models ensures that the data received and sent by the API
is validated, typed, and well-structured.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any


class ChatMessage(BaseModel):
    """
    Represents a single message in the conversation history, adhering to
    the structure expected by the Gemini API.
    """
    role: str = Field(..., description="The role of the sender, either 'user' or 'model'.")
    parts: List[Dict[str, Any]] = Field(..., description="The content parts of the message.")


class ChatRequest(BaseModel):
    """
    Defines the structure of the request body for a chat interaction.
    """
    message: str = Field(..., description="The new message sent by the user.", example="What is a notary public?")
    history: List[ChatMessage] = Field(default=[], description="The previous conversation history to maintain context.")

    # Replaces `Config` from v1
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ChatResponse(BaseModel):
    """
    Defines the structure of the response body sent back to the client.
    """
    reply: str = Field(..., description="The chatbot's generated response.", example="A notary public is a public officer...")
    history: List[ChatMessage] = Field(..., description="The updated conversation history, including the latest exchange.")

    # Add here too if needed
    model_config = ConfigDict(arbitrary_types_allowed=True)
