from pydantic import BaseModel
from datetime import datetime

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    timestamp: str  # ISO string
