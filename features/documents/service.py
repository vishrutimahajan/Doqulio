
import datetime,re,pdfplumber
from docx import Document
from firebase_admin import firestore
from core.gcs import upload_file, download_file
import google.generativeai as gemini
from core.firebase import db  # <- import the already initialized db ///////
from core.config import GEMINI_API_KEY
from google.cloud import storage
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status 
import tempfile
import os
# --- Patterns for redaction --- ########
patterns = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b\d{10}\b",
    "aadhaar": r"\b\d{4}\s\d{4}\s\d{4}\b",
    "pan": r"[A-Z]{5}[0-9]{4}[A-Z]{1}",
     "pincode": r"\b\d{6}\b",  # Indian postal codes
    "house_no": r"\b(?:Flat|House|Plot|No\.?|#)\s?\d+[A-Za-z0-9/-]*\b",
    "street": r"\b(?:Street|St|Road|Rd|Nagar|Colony|Avenue|Ave|Lane|Ln|Block)\b.*"
}

db = firestore.client()
gemini.api_key = ".."

storage_client = storage.Client()
BUCKET_NAME = "docquliobucket"

# ... other functions ...



def redact_text(text: str) -> str:
    """Apply regex patterns to redact sensitive info"""
    for _, pattern in patterns.items():
        text = re.sub(pattern, "[HIDDEN]", text)
    return text


def extract_text_from_file(local_path: str, mime_type: str) -> str:
    """Read file from local path and extract text based on type"""
    if mime_type == "application/pdf":
        text = ""
        with pdfplumber.open(local_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(local_path)
        return "\n".join([p.text for p in doc.paragraphs])

    elif mime_type.startswith("text/"):
        with open(local_path, "r", encoding="utf-8") as f:
            return f.read()

    else:
        raise ValueError(f"Unsupported file type: {mime_type}")


def parse_and_redact(local_path: str, mime_type: str) -> str:
    """Main function to parse and redact document"""
    raw_text = extract_text_from_file(local_path, mime_type)
    return redact_text(raw_text)




def upload_file_to_gcs(file_data: bytes, file_name: str, mime_type: str) -> str:
    """Uploads a file to GCS and returns its public URL."""
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_name)
        
        blob.upload_from_string(file_data, content_type=mime_type)
        
        # Make the file publicly accessible
        
        return f"https://storage.googleapis.com/{BUCKET_NAME}/{file_name}"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to cloud storage: {str(e)}"
        )

def download_file_from_gcs(blob_name: str, local_path: str):
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(local_path)
        return local_path
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GCS download failed: {str(e)}"
        )
def process_document(user_id: str, file_data: bytes, filename: str, document_type: str, mime_type: str):
    gcs_path = f"docs/{filename}"

    # 1️⃣ Upload file to GCS
    gcs_url = upload_file_to_gcs(file_data, gcs_path, mime_type)

    # 2️⃣ Save initial metadata in Firestore
    doc_ref = db.collection("users").document(user_id).collection("documents").document()
    doc_ref.set({
        "filename": filename,
        "document_type": document_type,
        "mime_type": mime_type,
        "gcs_url": gcs_url,
        "uploaded_at": datetime.datetime.utcnow(),
        "ai_summary": None,
        "risk_analysis": None
    })

    # 3️⃣ Download file locally in a temp directory
    temp_dir = tempfile.gettempdir()
    local_path = os.path.join(temp_dir, filename)
    download_file_from_gcs(gcs_path, local_path)

    # 4️⃣ Extract and redact content
    content = extract_text_from_file(local_path, mime_type)
    redacted_content = redact_text(content)

    # 5️⃣ Generate AI summary
    model_summary = gemini.GenerativeModel("gemini-1.5-flash")
    summary_response = model_summary.generate_content(
        f"Summarize this {document_type} document:\n{redacted_content}"
    )
    summary = summary_response.text.strip()

    # 6️⃣ Risk analysis
    model_risk = gemini.GenerativeModel("gemini-1.5-flash")
    risk_response = model_risk.generate_content(
        f"Analyze legal risks in this {document_type} document:\n{redacted_content}"
    )
    risk_result = {
        "risk_score": 0.7,  # placeholder
        "issues_found": [risk_response.text.strip()],
        "recommendations": ["Review highlighted issues"]
    }

    # 7️⃣ Update Firestore
    doc_ref.update({
        "ai_summary": summary,
        "summary_generated_at": datetime.datetime.utcnow(),
        "risk_analysis": risk_result
    })

    # 8️⃣ Return results
    return {
        "doc_id": doc_ref.id,
        "gcs_url": gcs_url,
        "summary": summary,
        "risk_analysis": risk_result
    }