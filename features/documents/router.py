from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PyPDF2 import PdfReader
import requests
from core.config import GEMINI_API_KEY
from .service import parse_and_redact

router = APIRouter(prefix="/documents", tags=["Documents"])


# -------------------- Helpers --------------------
def read_pdf(file) -> str:
    """Extract text from uploaded PDF file"""
    try:
        reader = PdfReader(file)
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

    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

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
Summarize the following legal document focusing only on:

1. Key parties involved  
2. Important dates and deadlines  
3. Main obligations of each party  
4. Risks and liabilities  
5. Termination and renewal clauses  

Document:
{text}
"""
    return call_gemini(prompt)


def check_risk(text: str) -> str:
    prompt = f"""
Identify potential legal, compliance, or financial risks in the following document.
Be specific and concise:

{text}
"""
    return call_gemini(prompt)


# -------------------- Endpoints --------------------
@router.post("/redact")
async def redact_document(file: UploadFile = File(...), document_type: str = Form(...)):
    """Redacts sensitive info and returns clean text"""
    try:
        redacted_text = parse_and_redact(file.file, file.content_type)
        return {
            "filename": file.filename,
            "document_type": document_type,
            "redacted_text": redacted_text,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze")
async def analyze_document(file: UploadFile = File(...), document_type: str = Form(...)):
    """Extracts text, summarizes, and checks risks"""
    if document_type.lower() != "pdf":
        return {"error": "Only PDF files are supported for now"}

    try:
        # Step 1: Read PDF
        text = read_pdf(file.file)

        # Step 2: Redact
        redacted_text = parse_and_redact(file.file, file.content_type)

        # Step 3: Summarize
        summary = summarize_document(text)

        # Step 4: Risk Analysis
        risks = check_risk(text)

        return {
            "filename": file.filename,
            "document_type": document_type,
            "summary": summary,
            "risks": risks,
            "redacted_text": redacted_text,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
