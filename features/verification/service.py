import os
import json
import logging
from io import BytesIO
from dotenv import load_dotenv

# --- Imports for PDF processing and generation ---
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Required Libraries ---
# pip install google-cloud-vision google-generativeai python-dotenv pydantic Pillow PyMuPDF reportlab
from google.cloud import vision
import google.generativeai as genai

# --- Schemas ---
from .schemas import VerificationReport, VerificationStatus

# --- Environment Variable Configuration ---
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    logging.error(f"Error configuring Gemini API: {e}")


class DocumentVerificationService:
    """
    Service class to handle document verification, redaction, scoring, and report generation.
    """
    def __init__(self):
        self.vision_client = vision.ImageAnnotatorClient()
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')

    def _extract_text_from_document(self, content: bytes, filename: str) -> str:
        # This method is unchanged.
        try:
            full_text = []
            if filename.lower().endswith('.pdf'):
                pdf_document = fitz.open(stream=content, filetype="pdf")
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    pix = page.get_pixmap()
                    img_bytes = pix.tobytes("png")
                    image = vision.Image(content=img_bytes)
                    response = self.vision_client.text_detection(image=image)
                    if response.error.message:
                        raise Exception(f"Vision API Error on page {page_num + 1}: {response.error.message}")
                    if response.full_text_annotation:
                        full_text.append(response.full_text_annotation.text)
                return "\n".join(full_text)
            else:
                image = vision.Image(content=content)
                response = self.vision_client.text_detection(image=image)
                if response.error.message:
                    raise Exception(f"Vision API Error: {response.error.message}")
                return response.full_text_annotation.text if response.full_text_annotation else ""
        except Exception as e:
            logging.error(f"Error during OCR extraction for {filename}: {e}")
            return ""

    # --- MODIFIED: Prompt is now much more intelligent and selective ---
    def _redact_sensitive_info(self, text: str) -> str:
        """
        Uses Gemini to intelligently find and redact only high-risk PII,
        preserving context and readability.
        """
        if not text:
            return ""
        
        prompt = f"""
        You are a data privacy expert. Your task is to intelligently redact only the most sensitive, non-public information from the following text, while preserving the overall context and readability. Do not redact everything; only remove information that poses a significant privacy risk if shared.

        **Redaction Rules:**
        1.  **ALWAYS REDACT (replace with "[REDACTED]"):**
            -   Social Security Numbers (SSNs), Taxpayer Identification Numbers (TINs).
            -   Driver's License, Passport, or other government ID numbers.
            -   Bank account numbers, routing numbers, and credit/debit card numbers.
            -   Full dates of birth (e.g., "Jan 1, 1990" becomes "[REDACTED]").
            -   Personal phone numbers and personal email addresses (e.g., @gmail.com, @yahoo.com).

        2.  **REDACT WITH CAUTION:**
            -   Full street addresses (e.g., "123 Main St, Anytown, USA 12345"). You may leave the city/country for context.
            -   Full names of individuals. If a name is essential for understanding the document's purpose (e.g., an invoice addressed to a client), you should LEAVE it. Only redact names if they are mentioned incidentally or in a list where they are not the main subject.

        3.  **DO NOT REDACT:**
            -   Company names or organization names.
            -   General dates (e.g., invoice date, contract start date).
            -   Monetary amounts, item descriptions, or transaction details.
            -   Business email addresses (e.g., contact@company.com).
            -   General business correspondence language.

        **Your Goal:** Return the text with only the highest-risk data replaced by "[REDACTED]". The output should be readable and retain as much of its original meaning as possible.

        **Original Text:**
        ---
        {text}
        ---

        **Intelligently Redacted Text:**
        """
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logging.error(f"Error during intelligent redaction: {e}")
            return "Redaction failed due to an internal error."

    def _analyze_text_with_gemini(self, text: str, description: str) -> dict:
        # This method is unchanged.
        if not text:
            return {
                "status": VerificationStatus.ERROR.value,
                "summary": "OCR failed to extract text.",
                "details": "Could not extract any text from the document.",
                "confidence_score": 0
            }
        prompt = f"""
        You are a document fraud analyst. Analyze the text for signs of forgery or inconsistencies.
        **User's Description:** "{description}"
        **Extracted Document Text:** --- {text} ---
        **Instructions:** Provide a JSON response with four keys: 'status' (one of ["VERIFIED", "SUSPICIOUS", "INDETERMINATE"]),
        'summary' (a one-sentence conclusion), 'details' (a bullet-pointed explanation), and
        'confidence_score' (an integer 0-100 for your confidence in the status).
        Your JSON response:
        """
        raw_response_text = ""
        try:
            response = self.gemini_model.generate_content(prompt)
            raw_response_text = response.parts[0].text if response.parts else ""
            cleaned_response = raw_response_text.strip().replace("```json", "").replace("```", "")
            return json.loads(cleaned_response)
        except (json.JSONDecodeError, IndexError, Exception) as e:
            logging.error(f"Error parsing Gemini response: {e}")
            logging.error(f"--- FAULTY AI RESPONSE TEXT --- \n{raw_response_text}\n-----------------------------")
            return { "status": VerificationStatus.ERROR.value, "summary": "AI analysis failed.", "details": "The AI model's output was not valid JSON.", "confidence_score": 0 }

    def verify_document(self, file_content: bytes, filename: str, description: str) -> VerificationReport:
        # This orchestration method is unchanged.
        extracted_text = self._extract_text_from_document(content=file_content, filename=filename)
        analysis_result = self._analyze_text_with_gemini(text=extracted_text, description=description)
        redacted_summary = self._redact_sensitive_info(analysis_result.get("summary", ""))
        redacted_extracted_text = self._redact_sensitive_info(extracted_text)
        analysis_details_raw = analysis_result.get("details", "No details available.")
        analysis_details_str = "\n".join(analysis_details_raw) if isinstance(analysis_details_raw, list) else str(analysis_details_raw)
        
        report = VerificationReport(
            filename=filename,
            verification_status=analysis_result.get("status", VerificationStatus.ERROR),
            confidence_score=analysis_result.get("confidence_score", 0),
            summary=redacted_summary or "Analysis could not be completed.",
            analysis_details=analysis_details_str,
            extracted_text=redacted_extracted_text or "No text could be extracted."
        )
        return report

    def generate_pdf_report(self, report_data: VerificationReport) -> BytesIO:
        # This PDF generation method is unchanged.
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica-Bold", 16)
        c.drawString(inch, height - inch, "Document Verification Report")
        c.line(inch, height - inch - 5, width - inch, height - inch - 5)
        styles = getSampleStyleSheet()
        style_body = styles['BodyText']
        style_body.leading = 14
        report_items = [
            ("Filename:", report_data.filename),
            ("Verification Status:", report_data.verification_status.value),
            ("Confidence Score:", f"{report_data.confidence_score}%"),
            ("Summary:", report_data.summary)
        ]
        text_y = height - 1.5 * inch
        for label, value in report_items:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(inch, text_y, label)
            p = Paragraph(value, style_body)
            p_width, p_height = p.wrapOn(c, width - 3.5 * inch, height)
            p.drawOn(c, inch + 1.5*inch, text_y - (p_height/2) + 2)
            text_y -= (p_height + 0.25 * inch)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(inch, text_y, "Analysis Details:")
        text_y -= 0.25 * inch
        p_details = Paragraph(report_data.analysis_details.replace('\n', '<br/>'), style_body)
        p_width_details, p_height_details = p_details.wrapOn(c, width - 2 * inch, height)
        p_details.drawOn(c, inch, text_y - p_height_details)
        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer

# Create a single instance of the service
verification_service = DocumentVerificationService()