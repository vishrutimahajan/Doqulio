# schemas.py

from pydantic import BaseModel
from enum import Enum

# --- MODIFIED: The Enum now holds the full, user-friendly names ---
class Language(str, Enum):
    """
    An enumeration for supported languages. The values are now the full names
    which will be displayed in the API documentation's dropdown menu.
    """
    HINDI = "Hindi"
    TAMIL = "Tamil"
    TELUGU = "Telugu"
    KANNADA = "Kannada"
    MALAYALAM = "Malayalam"
    MARATHI = "Marathi"
    BENGALI = "Bengali"
    GUJARATI = "Gujarati"
    PUNJABI = "Punjabi"
    ODIA = "Odia"
    ASSAMESE = "Assamese"
    URDU = "Urdu"
    SANSKRIT = "Sanskrit"
    ENGLISH = "English"

# --- ADDED: A mapping to get the API code from the full name ---
LANGUAGE_CODE_MAP = {
    Language.HINDI: "hi",
    Language.TAMIL: "ta",
    Language.TELUGU: "te",
    Language.KANNADA: "kn",
    Language.MALAYALAM: "ml",
    Language.MARATHI: "mr",
    Language.BENGALI: "bn",
    Language.GUJARATI: "gu",
    Language.PUNJABI: "pa",
    Language.ODIA: "or",
    Language.ASSAMESE: "as",
    Language.URDU: "ur",
    Language.SANSKRIT: "sa",
    Language.ENGLISH: "en",
}


class ChatResponse(BaseModel):
    """
    Defines the structure for the JSON response sent back to the client.
    """
    response: str

    class Config:
        schema_extra = {
            "example": {
                "response": "This is a summary of your legal document..."
            }
        }