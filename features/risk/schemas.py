from pydantic import BaseModel
from typing import List

class RiskCheckRequest(BaseModel):
    document_url: str
    document_type: str

class RiskCheckResponse(BaseModel):
    risk_score: float
    issues_found: List[str]
    recommendations: List[str]
