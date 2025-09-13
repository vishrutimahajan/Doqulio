import os
import io
import docx
import google.generativeai as genai
from fastapi import HTTPException, UploadFile, status
from PIL import Image
from pypdf import PdfReader
from google.cloud import translate_v2 as translate

# --- AI Configuration ---
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except KeyError:
    raise RuntimeError("GEMINI_API_KEY environment variable not set.")

# --- Initialize the Translation client ---
try:
    translate_client = translate.Client()
except Exception as e:
    raise RuntimeError(f"Failed to initialize Google Translate client. Ensure authentication is configured. Error: {str(e)}")


def extract_text_from_file(file: UploadFile) -> str:
    """
    Extracts text content from a DOCX file.
    This function is only used for DOCX as Gemini does not natively
    support it via direct file upload.
    """
    try:
        file.file.seek(0)
        doc = docx.Document(io.BytesIO(file.file.read()))
        file.file.seek(0)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process DOCX file: {str(e)}"
        )

def translate_text(text: str, target_language: str) -> str:
    """
    Translates text into the target language using Google Cloud Translation API.
    """
    if not text or not target_language:
        return text
    try:
        result = translate_client.translate(text, target_language=target_language)
        return result['translatedText']
    except Exception as e:
        print(f"Warning: Translation to '{target_language}' failed: {str(e)}")
        return text

def generate_chat_response(prompt: str, document_text: str | None = None, file_data: bytes | None = None, mime_type: str | None = None, target_language: str | None = None) -> str:
    """
    Generates a response from the Gemini AI based on the user prompt and optional context.
    Optionally translates the response to the target language.
    """
    # --- MODIFIED SYSTEM PROMPT ---
    # This prompt now guides the AI to handle both document analysis and general queries.
    system_prompt = """
    You are 'Doqulio', a friendly and helpful AI legal assistant. Your main goal is to demystify complex legal jargon and answer legal questions for users.

    Your primary function is to act in one of two ways:

    1.  **If a document is provided:** Your task is to carefully analyze and summarize it. Generate a detailed report with key findings (e.g., for a rental agreement, this would include owner's name, borrower's name, commencement date, expiry date, etc.). You must also assess the document's authenticity and state it as a percentage. Pay close attention to all terms and conditions, and create a separate note for any clauses that require special attention.

    2.  **If NO document is provided:** Your task is to answer the user's general question directly and helpfully. Provide clear, easy-to-understand explanations for legal concepts or queries like 'what is a rental agreement?'.

    Always be friendly and professional.
    """

    contents = [system_prompt]

    if document_text:
        contents.append(f"--- DOCUMENT CONTEXT ---\n{document_text}\n--- END OF DOCUMENT ---\n")
    
    if file_data and mime_type:
        if "image" in mime_type:
            contents.append(Image.open(io.BytesIO(file_data)))
        elif "pdf" in mime_type:
            contents.append({
                'mime_type': mime_type,
                'data': file_data
            })

    contents.append(f"User's question: {prompt}")

    try:
        response = model.generate_content(contents)
        generated_text = response.text

        if target_language:
            return translate_text(generated_text, target_language)
        
        return generated_text
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error communicating with the AI service: {str(e)}"
        )