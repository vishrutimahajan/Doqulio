from fastapi import APIRouter, Depends, HTTPException
from .schemas import ChatRequest, ChatResponse
from .service import get_ai_response, get_user_history
from features.auth.dependencies import get_current_user
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/ask", response_model=ChatResponse)
def ask_question(request: ChatRequest, user=Depends(get_current_user)):
    try:
        answer = get_ai_response(user["uid"], request.question)
        return ChatResponse(answer=answer, timestamp=datetime.utcnow().isoformat())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history", response_model=list[ChatResponse])
def get_chat_history(user=Depends(get_current_user)):
    try:
        history = get_user_history(user["uid"])
        return [
            ChatResponse(answer=h["answer"], timestamp=h["timestamp"].isoformat())
            for h in history
        ]
    except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
