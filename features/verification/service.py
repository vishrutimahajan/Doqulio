# service.py

import os
import json
import logging
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv

# --- Imports for PDF processing and generation ---
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Required Libraries ---
# pip install google-cloud-vision google-generativeai python-dotenv pydantic Pillow PyMuPDF reportlab google-cloud-storage langdetect
from google.cloud import vision, storage
import google.generativeai as genai
from langdetect import detect, LangDetectException

# --- Schemas ---
from features.verification.schemas import VerificationReport, VerificationStatus

# --- Font Registration for PDF Generation ---
# Register fonts for all supported languages
fonts_base_dir = os.path.join(os.path.dirname(__file__), 'fonts')

# Font family mapping for supported languages
LANGUAGE_FONT_MAP = {
    'hi': 'NotoSansDevanagari',  # Hindi
    'bn': 'NotoSansBengali',     # Bengali
    'mr': 'NotoSansDevanagari',  # Marathi (uses Devanagari script)
    'te': 'NotoSansTelugu',      # Telugu
    'ta': 'NotoSansTamil',       # Tamil
    'gu': 'NotoSansGujarati',    # Gujarati
    'kn': 'NotoSansKannada',     # Kannada
    'ml': 'NotoSansMalayalam',   # Malayalam
    'pa': 'NotoSansGurmukhi',    # Punjabi (uses Gurmukhi script)
    'en': 'Poppins'              # English
}

try:
    # Register all font families
    for lang_code, font_family in LANGUAGE_FONT_MAP.items():
        if font_family == 'Poppins':
            font_dir = os.path.join(fonts_base_dir, font_family)
            regular_font = os.path.join(font_dir, f'{font_family}-Regular.ttf')
            bold_font = os.path.join(font_dir, f'{font_family}-Bold.ttf')
        else:
            # Map font family to directory name
            if font_family == 'NotoSansGurmukhi':
                dir_name = 'Noto_Sans_Gurmukhi'
            elif font_family == 'NotoSansBengali':
                dir_name = 'Noto_Sans_Bengali'
            elif font_family == 'NotoSansDevanagari':
                dir_name = 'Noto_Sans_Devanagari'
            elif font_family == 'NotoSansTelugu':
                dir_name = 'Noto_Sans_Telugu'
            elif font_family == 'NotoSansTamil':
                dir_name = 'Noto_Sans_Tamil'
            elif font_family == 'NotoSansGujarati':
                dir_name = 'Noto_Sans_Gujarati'
            elif font_family == 'NotoSansKannada':
                dir_name = 'Noto_Sans_Kannada'
            elif font_family == 'NotoSansMalayalam':
                dir_name = 'Noto_Sans_Malayalam'
            else:
                dir_name = f'Noto_Sans_{font_family.replace("NotoSans", "")}'
            
            font_dir = os.path.join(fonts_base_dir, dir_name, 'static')
            regular_font = os.path.join(font_dir, f'{font_family}-Regular.ttf')
            bold_font = os.path.join(font_dir, f'{font_family}-Bold.ttf')
            
        if os.path.exists(regular_font) and os.path.exists(bold_font):
            pdfmetrics.registerFont(TTFont(font_family, regular_font))
            pdfmetrics.registerFont(TTFont(f'{font_family}-Bold', bold_font))
            pdfmetrics.registerFontFamily(font_family, normal=font_family, bold=f'{font_family}-Bold')
            logging.info(f"Successfully registered {font_family} font family for {lang_code}")
        else:
            # Try alternative naming patterns
            alt_regular = os.path.join(font_dir, f'NotoSans{font_family.replace("NotoSans", "")}-Regular.ttf')
            alt_bold = os.path.join(font_dir, f'NotoSans{font_family.replace("NotoSans", "")}-Bold.ttf')
            
            if os.path.exists(alt_regular) and os.path.exists(alt_bold):
                pdfmetrics.registerFont(TTFont(font_family, alt_regular))
                pdfmetrics.registerFont(TTFont(f'{font_family}-Bold', alt_bold))
                pdfmetrics.registerFontFamily(font_family, normal=font_family, bold=f'{font_family}-Bold')
                logging.info(f"Successfully registered {font_family} font family for {lang_code} (alt naming)")
            else:
                logging.warning(f"Could not find font files for {font_family} ({lang_code})")
                logging.warning(f"Looking for: {regular_font} and {bold_font}")
                logging.warning(f"Also tried: {alt_regular} and {alt_bold}")
            
    logging.info("Completed font registration for all supported languages")
except Exception as e:
    logging.error(f"Error during font registration: {e}")
    logging.warning("PDFs with non-Latin text may not render correctly")



class DocumentVerificationService:
    def __init__(self):
        self.vision_client = vision.ImageAnnotatorClient()
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')

        try:
            self.storage_client = storage.Client()
            self.bucket_name = os.getenv("GCS_BUCKET_NAME")
            if not self.bucket_name:
                logging.warning("GCS BUCKET_NAME not set.")
                self.bucket = None
            else:
                self.bucket = self.storage_client.bucket(self.bucket_name)
        except Exception as e:
            logging.error(f"GCS client init error: {e}")
            self.bucket = None

        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        except Exception as e:
            logging.error(f"Gemini API config error: {e}")
            raise ConnectionError("Could not configure Gemini API.") from e
    
    def _upload_redacted_to_gcs(self, redacted_text: str, filename: str, user_id: str) -> str | None:
        """Uploads only the redacted text file to GCS under docs/{user_id}/filename.txt"""
        if not self.bucket:
            logging.info("Skipping GCS upload (bucket not configured).")
            return None
        try:
            blob_path = f"docs/{user_id}/{filename}.txt"
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(redacted_text.encode("utf-8"))
            logging.info(f"Uploaded redacted file to GCS at {blob_path}",content_type="text/plain")
            logging.info(f"Upload successful: {blob_path}")

            return blob.public_url
        except Exception as e:
            logging.error(f"Failed to upload redacted file {filename} for {user_id}. Error: {e}")

            return None

    def _detect_language(self, text: str) -> str:
        """Detects the language of the given text, defaulting to English."""
        if not text or not text.strip():
            return "en"
        try:
            # Use a sample of the text for efficiency
            sample = text[:500]
            return detect(sample)
        except LangDetectException:
            logging.warning("Language detection failed. Defaulting to 'en'.")
            return "en"

    def _extract_text_from_document(self, content: bytes, filename: str) -> str:
        """Extracts text from PDF or image files using Google Cloud Vision OCR."""
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

    def _redact_sensitive_info(self, text: str, language: str = "en") -> str:
        """Uses Gemini to intelligently find and redact high-risk PII."""
        if not text:
            return ""
        prompt = f"""
        You are a data privacy expert. Your task is to intelligently redact only the most sensitive, non-public information from the following text, while preserving the overall context and readability. The text is in the language '{language}'.
        **Redaction Rules:**
        1. **ALWAYS REDACT (replace with "[REDACTED]"):** Social Security Numbers, Tax IDs, national ID numbers, Driver's License/Passport numbers, Bank account/credit card numbers, Full dates of birth, Personal phone numbers and personal email addresses.
        2. **REDACT WITH CAUTION:** Full street addresses (you may leave city/country). Full names of individuals, only if mentioned incidentally. If they are the main subject (e.g., invoice recipient), LEAVE the name.
        3. **DO NOT REDACT:** Company/organization names, General dates (e.g., invoice date), Monetary amounts or transaction details, Business contact information.
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

    def _analyze_text_with_gemini(self, text: str, description: str, detected_language: str, output_language: str) -> dict:
        """Analyzes text and generates the findings in the user-specified output language."""
        if not text:
            error_summary = "OCR failed to extract any text from the document."
            error_details = ["- No text was available for analysis."]
            if output_language != "en":
                try:
                    translation_prompt = f"Translate the following JSON values into the language '{output_language}': {json.dumps({'summary': error_summary, 'details': error_details})}"
                    translated_response = self.gemini_model.generate_content(translation_prompt)
                    translated_data = json.loads(translated_response.text)
                    error_summary = translated_data.get('summary', error_summary)
                    error_details = translated_data.get('details', error_details)
                except Exception as e:
                    logging.error(f"Failed to translate error message: {e}")
            return {
                "status": VerificationStatus.ERROR.value,
                "summary": error_summary,
                "details": error_details,
                "confidence_score": 0
            }

        prompt = f"""
        Act as a forensic document examiner. Your task is to analyze the source text and provide your findings in a specific target language.
        **CONTEXT:**
        - **Source Text Language:** `{detected_language}`
        - **User's Claim:** The document is a "{description}".
        - **Target Report Language:** `{output_language}`
        **ANALYSIS INSTRUCTIONS (Perform these mentally on the source text):**
        1.  **Assess Plausibility:** Does the content align with a typical "{description}"?
        2.  **Check for Inconsistencies:** Look for contradictions in dates, numbers, or logic.
        3.  **Identify Linguistic Red Flags:** Search for unusual grammar, spelling errors, or an unprofessional tone in the source text.
        4.  **Evaluate Data Points:** Scrutinize names, addresses, and identifiers for generic or fake-looking entries.
        5.  **Formulate Verdict:** Based on the evidence, decide on a status ('VERIFIED', 'SUSPICIOUS', 'INDETERMINATE') and a confidence score.
        **RESPONSE FORMAT (Crucial):**
        Provide a single, valid JSON object. The 'summary' and 'details' fields **MUST** be written in the target language: **`{output_language}`**. Do not include any explanations outside of the JSON structure.
        {{
          "status": "one of ['VERIFIED', 'SUSPICIOUS', 'INDETERMINATE']",
          "summary": "A one-sentence conclusion written in **{output_language}**.",
          "details": [
            "A bullet point list of your specific findings, written in **{output_language}**.",
            "Explain the key factors that led to your status decision, also in **{output_language}**."
          ],
          "confidence_score": "An integer between 0 and 100."
        }}
        **Source Document Text:**
        ---
        {text}
        ---
        Your JSON response:
        """
        raw_response_text = ""
        try:
            response = self.gemini_model.generate_content(prompt)
            raw_response_text = response.text
            cleaned_response = raw_response_text.strip().replace("```json", "").replace("```", "")
            return json.loads(cleaned_response)
        except (json.JSONDecodeError, AttributeError, Exception) as e:
            logging.error(f"Error parsing Gemini analysis response: {e}")
            logging.error(f"--- FAULTY AI RESPONSE TEXT --- \n{raw_response_text}\n-----------------------------")
            return {
                "status": VerificationStatus.ERROR.value,
                "summary": "AI analysis failed due to an invalid response format.",
                "details": [f"Error: {e}", f"Raw response: {raw_response_text}"],
                "confidence_score": 0
            }

    def verify_document(
    self, file_content: bytes, filename: str, description: str, output_language: str, user_id: str
) -> VerificationReport:
        """Orchestrates the full document verification workflow with user-selected output language.
    """
        # 1. Extract text from the document (OCR)
        extracted_text = self._extract_text_from_document(content=file_content, filename=filename)

        # 2. Detect language of the extracted text
        detected_language = self._detect_language(extracted_text)

        # 3. Redact sensitive information
        redacted_extracted_text = self._redact_sensitive_info(extracted_text, detected_language)

        # 4. Upload ONLY the redacted text file to GCS
        storage_url = self._upload_redacted_to_gcs(
            redacted_text=redacted_extracted_text,
            filename=filename,
            user_id=user_id
        )

        # 5. Analyze text with Gemini for verification
        analysis_result = self._analyze_text_with_gemini(
            text=redacted_extracted_text,
            description=description,
            detected_language=detected_language,
            output_language=output_language,
        )

        # 6. Format analysis details
        analysis_details_raw = analysis_result.get("details", "No details available.")
        analysis_details_str = (
            "\n".join(f"- {item}" for item in analysis_details_raw)
            if isinstance(analysis_details_raw, list)
            else str(analysis_details_raw)
        )

        # 7. Build the final verification report
        report = VerificationReport(
            filename=filename,
            storage_url=storage_url,
            detected_language=detected_language,
            report_language=output_language,
            verification_status=analysis_result.get("status", VerificationStatus.ERROR),
            confidence_score=analysis_result.get("confidence_score", 0),
            summary=analysis_result.get("summary", "Analysis could not be completed."),
            analysis_details=analysis_details_str,
            extracted_text=redacted_extracted_text or "No text could be extracted."
        )

        return report
   
      

    def generate_pdf_report(self, report_data: VerificationReport) -> BytesIO:
        """Generates a PDF report using language-specific fonts."""
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Get the appropriate font family for the report language
        report_font = LANGUAGE_FONT_MAP.get(report_data.report_language, 'Poppins')
        header_font = 'Poppins'  # Use Poppins for headers

        # Ensure fonts are registered before use
        fonts_base_dir = os.path.join(os.path.dirname(__file__), 'fonts')
        
        # Register the specific font needed for this report
        if report_font != 'Poppins':
            if report_font == 'NotoSansGurmukhi':
                dir_name = 'Noto_Sans_Gurmukhi'
            elif report_font == 'NotoSansBengali':
                dir_name = 'Noto_Sans_Bengali'
            elif report_font == 'NotoSansDevanagari':
                dir_name = 'Noto_Sans_Devanagari'
            elif report_font == 'NotoSansTelugu':
                dir_name = 'Noto_Sans_Telugu'
            elif report_font == 'NotoSansTamil':
                dir_name = 'Noto_Sans_Tamil'
            elif report_font == 'NotoSansGujarati':
                dir_name = 'Noto_Sans_Gujarati'
            elif report_font == 'NotoSansKannada':
                dir_name = 'Noto_Sans_Kannada'
            elif report_font == 'NotoSansMalayalam':
                dir_name = 'Noto_Sans_Malayalam'
            else:
                dir_name = f'Noto_Sans_{report_font.replace("NotoSans", "")}'
            
            font_dir = os.path.join(fonts_base_dir, dir_name, 'static')
            regular_font = os.path.join(font_dir, f'{report_font}-Regular.ttf')
            bold_font = os.path.join(font_dir, f'{report_font}-Bold.ttf')
            
            if os.path.exists(regular_font) and os.path.exists(bold_font):
                try:
                    pdfmetrics.registerFont(TTFont(report_font, regular_font))
                    pdfmetrics.registerFont(TTFont(f'{report_font}-Bold', bold_font))
                    pdfmetrics.registerFontFamily(report_font, normal=report_font, bold=f'{report_font}-Bold')
                except Exception as e:
                    logging.warning(f"Font registration failed for {report_font}: {e}")
                    # Fallback to Poppins
                    report_font = 'Poppins'

        # --- Create Paragraph styles using language-specific font ---
        styles = getSampleStyleSheet()
        style_body = ParagraphStyle(
            'BodyText',
            parent=styles['BodyText'],
            fontName=report_font,
            leading=14
        )
        style_bold = ParagraphStyle(
            'BodyTextBold',
            parent=style_body,
            fontName=f'{report_font}-Bold',
            leading=14
        )
        
        # --- PDF Header ---
        c.setFont(f"{header_font}-Bold", 16)
        c.drawString(inch, height - inch, "Document Verification Report")
        c.line(inch, height - inch - 5, width - inch, height - inch - 5)
        
        # --- Report Metadata ---
        report_items = [
            ("Filename:", report_data.filename),
            ("Storage URL:", report_data.storage_url or "N/A"),
            ("Source Language:", report_data.detected_language.upper()),
            ("Report Language:", report_data.report_language.upper()),
            ("Verification Status:", str(report_data.verification_status)),
            ("Confidence Score:", f"{report_data.confidence_score}%"),
            ("Summary:", report_data.summary)
        ]
        
        text_y = height - 1.75 * inch
        for label, value in report_items:
            # Render Label with header font
            c.setFont(f"{header_font}-Bold", 11)
            c.drawString(inch, text_y, label)
            
            # Render Value using a Paragraph with language-specific font
            p = Paragraph(str(value), style_body)
            p_width, p_height = p.wrapOn(c, width - 3.7 * inch, height)
            p.drawOn(c, inch + 1.7 * inch, text_y - (p_height / 2) + 2)
            
            text_y -= (p_height + 0.25 * inch)
            
        # --- Analysis Details Section ---
        c.setFont(f"{header_font}-Bold", 11)
        c.drawString(inch, text_y, "Analysis Details:")
        text_y -= 0.25 * inch
        
        p_details = Paragraph(report_data.analysis_details.replace('\n', '<br/>'), style_body)
        p_width_details, p_height_details = p_details.wrapOn(c, width - 2 * inch, height)
        
        if text_y - p_height_details < inch:
            c.showPage()
            text_y = height - inch
            c.setFont(f"{header_font}-Bold", 11)
            c.drawString(inch, text_y, "Analysis Details (Continued):")
            text_y -= 0.25 * inch

        p_details.drawOn(c, inch, text_y - p_height_details)
        
        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer

# Create a single instance of the service to be imported by the router
verification_service = DocumentVerificationService()

