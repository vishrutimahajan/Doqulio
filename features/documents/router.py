from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PyPDF2 import PdfReader
import requests
from core.config import GEMINI_API_KEY
from .service import parse_and_redact

router = APIRouter(prefix="/documents", tags=["Documents"])


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


def summarize_text(text: str) -> str:
    """Call Gemini AI to summarize text"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    headers = {"Content-Type": "application/json"}
    
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"""
Summarize the following legal document focusing only on:

1. Key parties involved  
2. Important dates and deadlines  
3. Main obligations of each party  
4. Risks and liabilities  
5. Termination and renewal clauses  

Document:
{text}
"""
                    }
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        raise ValueError(f"Gemini API request failed: {response.status_code}, {response.text}")

    result = response.json()
    summary = (
        result.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "No summary returned")
    )
    return summary

##############
@router.post("/redact")
async def redact_document(file: UploadFile = File(...), document_type: str = Form(...)):
    """
    Uploads a document, extracts text, redacts sensitive info, and returns clean text.
    """
    try:
        redacted_text = parse_and_redact(file.file, file.content_type)
        return {
            "filename": file.filename,
            "document_type": document_type,
            "redacted_text": redacted_text,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload-and-analyze")
async def upload_and_analyze(
    file: UploadFile = File(...),
    document_type: str = Form(...)
):
    if document_type.lower() != "pdf":
        return {"error": "Only PDF files are supported for now"}

    try:
        # Read PDF
        text = read_pdf(file.file)
    except ValueError as e:
        return {"error": str(e)}

    try:
        # Get AI summary
        summary = summarize_text(text)
    except ValueError as e:
        return {"error": str(e)}

    return {
        "filename": file.filename,
        "document_type": document_type,
        "summary": summary
    }
############