from fastapi import APIRouter, Depends, HTTPException
from .schemas import RiskCheckRequest, RiskCheckResponse
from .service import analyze_document
from features.auth.dependencies import get_current_user

router = APIRouter(prefix="/risk", tags=["Risk"])

@router.post("/check", response_model=RiskCheckResponse)
def check_risk(request: RiskCheckRequest, user=Depends(get_current_user)):
    try:
        result = analyze_document(user["uid"], request.document_url, request.document_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
