# core/chat_service.py

import os
import io
from typing import List, Dict, Any
from fastapi import HTTPException, UploadFile, status
from PIL import Image
import pytesseract
import docx
from pypdf import PdfReader
import google.generativeai as genai
from .schemas import ChatResponse

# --- AI Configuration ---
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    raise RuntimeError("GEMINI_API_KEY environment variable not set.")

# --- Gov links ---
gov_links = {
    "pan card": "https://www.onlineservices.nsdl.com/paam/endUserRegisterContact.html",
    "aadhaar": "https://uidai.gov.in/",
    "passport": "https://www.passportindia.gov.in/",
    "income tax": "https://www.incometax.gov.in/",
}

# --- System Prompt ---
SYSTEM_PROMPT = """
You are "Doqulio," an AI assistant that simplifies and verifies documents.

Your role:
- Provide short, clear, and concise answers.
- Explain complex terms simply.
- Guide users step-by-step in document verification.
- Provide steps for obtaining legal documents.
- Provide instructions for verifying documents.

Key Rules:
- Do not provide legal/medical/financial advice.
- If unsure, say so.
- Never ask for personal info.
- If query matches government services, append relevant link.

Always end with:
“This is general information, not legal advice. Please consult a lawyer for personal guidance.”
"""

# --- File Processing ---
def extract_text_from_file(file: UploadFile) -> str:
    """
    Extracts text from PDF, DOCX, or Image.
    """
    content_type = file.content_type
    file_bytes = file.file.read()

    try:
        if content_type == "application/pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            return "\n".join([page.extract_text() or "" for page in reader.pages])

        elif content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]:
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([para.text for para in doc.paragraphs])

        elif content_type in ["image/jpeg", "image/png"]:
            image = Image.open(io.BytesIO(file_bytes))
            return pytesseract.image_to_string(image)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {content_type}. Please upload PDF, DOCX, or image."
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
        )

# --- Gov link matcher ---
def get_gov_link(user_query: str):
    user_query = user_query.lower()
    for keyword, link in gov_links.items():
        if keyword in user_query:
            return f"✅ Official resource: {link}"
    return None

# --- Chat Response ---
def generate_response(message: str, history: List[Dict[str, Any]], document_text: str | None = None) -> ChatResponse:
    """
    Generate chatbot response with optional document context.
    """
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT
        )
        chat = model.start_chat(history=history)

        # Include doc context if available
        if document_text:
            message = f"Here is document context:\n{document_text}\n\nUser query: {message}"

        response = chat.send_message(message)
        updated_history = chat.history

        serializable_history = [
            {"role": msg.role, "parts": [{"text": part.text} for part in msg.parts]}
            for msg in updated_history
        ]

        reply_text = response.text
        gov_link = get_gov_link(message)
        if gov_link:
            reply_text = f"{reply_text}\n\n{gov_link}"

        # Append disclaimer
        reply_text += "\n\n⚠️ This is general information, not legal advice. Please consult a lawyer for personal guidance."

        return ChatResponse(
            reply=reply_text,
            history=serializable_history
        )

    except Exception as e:
        print(f"Gemini API error: {e}")
        history.append({"role": "user", "parts": [{"text": message}]})
        history.append({"role": "model", "parts": [{"text": "I encountered an error, please try again later."}]})
        return ChatResponse(
            reply="I’m sorry, I encountered an error while processing your request. Please try again later.",
            history=history
        )
