# service.py

import os
import io
from PIL import Image
import pytesseract
import docx
from pypdf import PdfReader
import google.generativeai as genai
from fastapi import HTTPException, UploadFile, status

# --- AI Configuration ---
# Configure the Gemini API with the key from environment variables
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-pro')
except KeyError:
    raise RuntimeError("GEMINI_API_KEY environment variable not set.")


def extract_text_from_file(file: UploadFile) -> str:
    """
    Extracts text content from an uploaded file (PDF, DOCX, or Image).
    """
    content_type = file.content_type
    file_bytes = file.file.read()

    try:
        if content_type == "application/pdf":
            # Process PDF file
            reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text

        elif content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
            # Process DOCX file
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs])
            return text

        elif content_type in ["image/jpeg", "image/png"]:
            # Process Image file using OCR
            image = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
            return text

        else:
            # Handle unsupported file types
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {content_type}. Please upload a PDF, DOCX, or image file."
            )
    except Exception as e:
        # Catch potential processing errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process the uploaded file: {str(e)}"
        )


def generate_chat_response(prompt: str, document_text: str | None = None) -> str:
    """
    Generates a response from the Gemini AI based on the user prompt and optional document context.
    """
    # System prompt to define the chatbot's persona and task
    system_prompt = """
    You are 'Doqulio', a friendly and helpful AI legal assistant. Your main goal is to demystify complex legal jargon for users.

    Follow these rules:
    1.  **Prioritize Clarity:** Explain legal terms and clauses in simple, easy-to-understand language.
    2.  **Be Concise First:** Start with a summary or key points. Use bullet points for readability.
    3.  **Offer Depth:** End your concise explanation by stating that you can provide a more detailed explanation if the user asks for it.
    4.  **Use Context When Provided:** If document text is included, base your answers primarily on that text.
    5.  **General Knowledge for General Questions:** If no document is provided, answer general legal questions to the best of your ability.
    6.  **Disclaimer:** Always include a brief, friendly disclaimer at the end of your response, like: "Remember, I'm an AI assistant, not a lawyer. It's always a good idea to consult with a qualified legal professional for serious matters."
    """

    # Combine the system prompt, document context (if any), and user question
    if document_text:
        full_prompt = f"""
        {system_prompt}

        --- DOCUMENT CONTEXT ---
        {document_text}
        --- END OF DOCUMENT ---

        Based on the document provided, please answer the following user question: "{prompt}"
        """
    else:
        full_prompt = f"""
        {system_prompt}

        Please answer the following general question: "{prompt}"
        """

    try:
        # Generate content using the AI model
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        # Handle potential API errors
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error communicating with the AI service: {str(e)}"
        )