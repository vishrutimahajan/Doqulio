# backend/main.
import fastapi
from fastapi import FastAPI
from features.auth import router as auth_router
from features.documents.router import router as docs_router
from features.chat.router import router as chat_router
from features.verification.router import router as verification_router
from features.Media.router import router as media_router
app = FastAPI(title="Docqulio Chatbot API")

# Register routers
app.include_router(auth_router.router)
app.include_router(docs_router)
app.include_router(chat_router)
app.include_router(verification_router)
app.include_router(media_router)


@app.get("/")
def root():
    return {"message": "Backend running ✅"}
