import os
import io
import docx
import google.generativeai as genai
from fastapi import HTTPException, UploadFile, status
from PIL import Image
from pypdf import PdfReader
from google.cloud import translate_v2 as translate # --- ADDED FOR TRANSLATION ---

# --- AI Configuration ---
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except KeyError:
    raise RuntimeError("GEMINI_API_KEY environment variable not set.")

# --- ADDED FOR TRANSLATION: Initialize the Translation client ---
try:
    translate_client = translate.Client()
except Exception as e:
    # This will catch errors if authentication (e.g., GOOGLE_APPLICATION_CREDENTIALS) is not set up correctly.
    raise RuntimeError(f"Failed to initialize Google Translate client. Ensure authentication is configured. Error: {str(e)}")


def extract_text_from_file(file: UploadFile) -> str:
    """
    Extracts text content from a DOCX file.
    This function is only used for DOCX as Gemini does not natively
    support it via direct file upload.
    """
    try:
        # Reset file pointer to the beginning before reading
        file.file.seek(0)
        doc = docx.Document(io.BytesIO(file.file.read()))
        # Reset file pointer again in case it needs to be read again
        file.file.seek(0)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process DOCX file: {str(e)}"
        )

# --- ADDED FOR TRANSLATION: New function to handle text translation ---
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
        # If translation fails, return the original text instead of crashing.
        # You might want to log this error for debugging.
        print(f"Warning: Translation to '{target_language}' failed: {str(e)}")
        return text

# --- MODIFIED: Added 'target_language' parameter ---
def generate_chat_response(prompt: str, document_text: str | None = None, file_data: bytes | None = None, mime_type: str | None = None, target_language: str | None = None) -> str:
    """
    Generates a response from the Gemini AI based on the user prompt and optional context.
    Optionally translates the response to the target language.
    """
    system_prompt = """
    You are 'Doqulio', a friendly and helpful AI legal assistant. Your main goal is to demystify complex legal jargon for users.
    All the legal documents that will be uploaded, I want you to summarise them carefully .
    Generate a detailed report about the key findings for example if I upload a rental agreement then
    the findings would be the owners name , borrower name, date of commencement, date of agreement expiry ,etc.
    Also validate the authenticity of the documents, present how authentic this document is in percentage.
    Make sure you pay attention to all the terms and conditions .
    If there is anything that is needed to b paid attention make a separate note of it in the report
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

    contents.append(prompt)

    try:
        response = model.generate_content(contents)
        generated_text = response.text

        # --- ADDED FOR TRANSLATION: Translate the response if a language is specified ---
        if target_language:
            return translate_text(generated_text, target_language)
        
        return generated_text
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error communicating with the AI service: {str(e)}"
        )