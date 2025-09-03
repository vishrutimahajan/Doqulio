import re
import datetime
from docx import Document
import pdfplumber
from firebase_admin import firestore
from core.gcs import upload_file, download_file
import google.generativeai as gemini
from core.firebase import db  # <- import the already initialized db ///////

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


def process_document(user_id: str, file, document_type: str, mime_type: str):
    """
    Upload file to GCS, generate AI summary, perform risk analysis,
    and store metadata in Firestore.
    """
    filename = file.filename
    gcs_path = f"docs/{filename}"

    # 1️⃣ Upload file to GCS
    gcs_url = upload_file(file.file, gcs_path)

    # 2️⃣ Save metadata in Firestore
    doc_ref = db.collection("users").document(user_id).collection("documents").document()
    doc_ref.set({
        "filename": filename,
        "document_type": document_type,
        "gcs_url": gcs_url,
        "uploaded_at": datetime.datetime.utcnow(),
        "ai_summary": None,
        "risk_analysis": None
    })

    # 3️⃣ Download file locally for AI processing
    local_path = download_file(gcs_path)

    # 4️⃣ Extract + redact content
    content = extract_text_from_file(local_path, mime_type)
    redacted_content = redact_text(content)

    # 5️⃣ Generate AI summary
    summary_response = gemini.GenerativeModel("gemini-2.0").generate_content(
        f"Summarize this {document_type} document:\n{redacted_content}"
    )
    summary = summary_response.text.strip()

    # 6️⃣ Risk analysis via AI
    risk_response = gemini.GenerativeModel("gemini-1.5-pro").generate_content(
        f"Analyze legal risks in this {document_type} document:\n{redacted_content}"
    )
    risk_result = {
        "risk_score": 0.7,  # placeholder
        "issues_found": [risk_response.text.strip()],
        "recommendations": ["Review highlighted issues"]
    }

    # 7️⃣ Update Firestore document
    doc_ref.update({
        "ai_summary": summary,
        "summary_generated_at": datetime.datetime.utcnow(),
        "risk_analysis": risk_result
    })

    return {
        "doc_id": doc_ref.id,
        "gcs_url": gcs_url,
        "summary": summary,
        "risk_analysis": risk_result
    }


#####