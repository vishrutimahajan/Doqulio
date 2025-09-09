import os
import json
import logging
from enum import Enum
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables from a .env file at the start
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Make sure to install the required libraries:
# pip install google-cloud-vision google-generativeai python-dotenv pydantic Pillow
from google.cloud import vision
import google.generativeai as genai

# Assuming your schemas.py file looks something like this:
# from enum import Enum
# from pydantic import BaseModel, Field
#
# class VerificationStatus(str, Enum):
#     VERIFIED = "VERIFIED"
#     SUSPICIOUS = "SUSPICIOUS"
#     INDETERMINATE = "INDETERMINATE"
#     ERROR = "ERROR"
#
# class VerificationReport(BaseModel):
#     filename: str
#     verification_status: VerificationStatus
#     summary: str
#     analysis_details: str
#     extracted_text: str

# --- Schemas ---
# This import is assumed to be working in your project structure
from .schemas import VerificationReport, VerificationStatus


# --- Configuration ---
# IMPORTANT: Set these environment variables in your system.
# For Cloud Vision: GOOGLE_APPLICATION_CREDENTIALS="path/to/your/credentials.json"
# For Gemini: GEMINI_API_KEY="your_gemini_api_key"
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    logging.error(f"Error configuring Gemini API: {e}")
    # You might want to handle this more gracefully

class DocumentVerificationService:
    """
    Service class to handle the document verification logic.
    """
    def __init__(self):
        self.vision_client = vision.ImageAnnotatorClient()
        # FIX: Updated model name to a valid, current model. 'gemini-2.5-flash' is not a real model name.
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')

    def _extract_text_from_document(self, content: bytes) -> str:
        """
        Uses Google Cloud Vision OCR to extract text from a document image.
        """
        try:
            image = vision.Image(content=content)
            response = self.vision_client.text_detection(image=image)
            
            if response.error.message:
                raise Exception(f"Vision API Error: {response.error.message}")
            
            return response.full_text_annotation.text if response.full_text_annotation else ""
        except Exception as e:
            logging.error(f"Error during OCR extraction: {e}")
            return ""

    def _analyze_text_with_gemini(self, text: str, description: str) -> dict:
        """
        Uses Gemini to analyze the extracted text for tampering and fake content.
        """
        if not text:
            return {
                "status": VerificationStatus.ERROR,
                "summary": "OCR failed to extract text.",
                "details": "Could not extract any text from the document. The file might be blank, corrupted, or not a valid document image."
            }

        prompt = f"""
        You are an expert document fraud analyst. Your task is to analyze the extracted text from a user's document based on their provided description.

        Analyze the text for any signs of tampering, forgery, inconsistencies, fake content, or suspicious modifications. Pay close attention to:
        1.  Inconsistencies between the document text and the user's description.
        2.  Unusual formatting, illogical statements, or grammatical errors that might indicate forgery.
        3.  Conflicting information within the document itself (e.g., dates, amounts, names).

        **User's Description:** "{description}"

        **Extracted Document Text:**
        ---
        {text}
        ---

        **Instructions for your response:**
        Provide your analysis in a structured JSON format. The JSON object **MUST** have three keys: 'status', 'summary', and 'details'.
        - 'status': Must be one of ["{VerificationStatus.VERIFIED.value}", "{VerificationStatus.SUSPICIOUS.value}", "{VerificationStatus.INDETERMINATE.value}"].
        - 'summary': A one-sentence conclusion of your findings.
        - 'details': A detailed, bullet-pointed explanation of your reasoning. This can be a single string with newlines, or a list of strings.
        
        Your JSON response:
        """
        
        try:
            response = self.gemini_model.generate_content(prompt)
            # Clean the response to ensure it's valid JSON
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
            return json.loads(cleaned_response)
        except Exception as e:
            logging.error(f"Error parsing Gemini response: {e}")
            return {
                "status": VerificationStatus.ERROR.value,
                "summary": "AI analysis failed.",
                "details": f"The analysis could not be completed due to an internal error: {str(e)}"
            }

    def verify_document(self, file_content: bytes, filename: str, description: str) -> VerificationReport:
        """
        Orchestrates the document verification process.
        """
        extracted_text = self._extract_text_from_document(content=file_content)
        analysis_result = self._analyze_text_with_gemini(text=extracted_text, description=description)

        # --- FIX: PROCESS THE 'details' FIELD TO PREVENT Pydantic VALIDATION ERROR ---
        # Get the raw 'details' value, which could be a list or a string.
        analysis_details_raw = analysis_result.get("details", "No details available.")

        # Check if the details field is a list and join it into a single string.
        if isinstance(analysis_details_raw, list):
            # Join list items with a newline to preserve the bulleted format.
            analysis_details_str = "\n".join(analysis_details_raw)
        else:
            # If it's already a string (or another type), just convert it to a string.
            analysis_details_str = str(analysis_details_raw)
        # --- END OF FIX ---

        report = VerificationReport(
            filename=filename,
            verification_status=analysis_result.get("status", VerificationStatus.ERROR),
            summary=analysis_result.get("summary", "Analysis could not be completed."),
            analysis_details=analysis_details_str, # Use the processed string here
            extracted_text=extracted_text or "No text could be extracted."
        )
        return report

# Create a single instance of the service to be used by the application
verification_service = DocumentVerificationService()