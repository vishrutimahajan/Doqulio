from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from PyPDF2 import PdfReader
from core.config import GEMINI_API_KEY
from .service import parse_and_redact, process_document, upload_file_to_gcs
import requests
import tempfile
import os

router = APIRouter(prefix="/documents", tags=["Documents"])

# -------------------- Helpers --------------------
def read_pdf(file_path: str) -> str:
    """Extract text from a PDF file"""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {e}")


def call_gemini(prompt: str) -> str:
    """Send prompt to Gemini API"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise ValueError(f"Gemini API request failed: {response.status_code}, {response.text}")

    result = response.json()
    return (
        result.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "No response")
    )


def summarize_document(text: str) -> str:
    prompt = f"""
Summarize the following legal document focusing on:

1. Key parties
2. Important dates and deadlines
3. Main obligations
4. Risks and liabilities
5. Termination/renewal clauses

Document:
{text}
"""
    return call_gemini(prompt)


def check_risk(text: str) -> str:
    prompt = f"""
Identify potential legal, compliance, or financial risks in the following document. Be specific:

{text}
"""
    return call_gemini(prompt)


# -------------------- Endpoints --------------------
@router.post("/redact")
async def redact_document(file: UploadFile = File(...), document_type: str = Form(...)):
    """Redacts sensitive info and returns clean text"""
    try:
        # Save uploaded file to temp file
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            local_path = tmp.name

        redacted_text = parse_and_redact(local_path, file.content_type)

        # Cleanup
        os.remove(local_path)

        return {
            "filename": file.filename,
            "document_type": document_type,
            "redacted_text": redacted_text,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    user_id: str = Form(...)
):
    """Upload to GCS, redact, summarize, risk analysis, store metadata"""
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only PDF, DOCX, and TXT are supported."
        )

    try:
        # Save uploaded file to temp file
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file_bytes = await file.read()
            tmp.write(file_bytes)
            local_path = tmp.name

        # Upload to GCS
        gcs_path = f"docs/{user_id}/{file.filename}"
        gcs_url = upload_file_to_gcs(file_bytes, gcs_path, file.content_type)

        # Process & save metadata
        result = process_document(user_id, file_bytes, file.filename, document_type, file.content_type)

        # Extract text and redact
        text = read_pdf(local_path)
        redacted_text = parse_and_redact(local_path, file.content_type)

        # Summarize & risk analysis
        summary = summarize_document(text)
        risks = check_risk(text)

        # Cleanup
        os.remove(local_path)

        return {
            "filename": file.filename,
            "document_type": document_type,
            "mime_type": file.content_type,
            "redacted_text": redacted_text,
            "summary": summary,
            "risk_analysis": risks,
            "gcs_url": gcs_url,
            "uploaded_at": datetime.utcnow(),
            "ai_summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
