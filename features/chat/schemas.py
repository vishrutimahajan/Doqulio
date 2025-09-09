# schemas.py

from pydantic import BaseModel, Field

class ChatResponse(BaseModel):
    """
    Defines the structure for the chatbot's response.
    """
    answer: str = Field(
        ...,
        title="Chatbot Answer",
        description="The generated response from the chatbot based on the user's query and/or document.",
        example="A rental agreement is a legal contract between a landlord (property owner) and a tenant..."
    )