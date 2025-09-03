import google.generativeai as gemini
from core.gcs import download_file
from core.config import GEMINI_API_KEY
from fastapi import APIRouter

router = APIRouter()

def analyze_document(user_id: str, document_url: str, document_type: str):
    """
    Downloads a document from GCS and sends it to Gemini AI for risk analysis.
    """
    # Extract blob name from URL
    blob_name = "/".join(document_url.split("/")[-2:])

    # Download file
    local_path = download_file(blob_name)

    # Read content (for PDFs or Word docs, implement proper parsing)
    with open(local_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Risk analysis via AI
    response = gemini.generate(
        model="gemini-1",
        prompt=f"Analyze legal risk in this {document_type} document:\n{content}",
        max_tokens=500
    )

    answer = response.text.strip()

    return {
        "risk_score": 0.7,
        "issues_found": [answer],
        "recommendations": ["Review the highlighted issues"]
    }
