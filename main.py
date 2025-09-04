# backend/main.
import fastapi
from fastapi import FastAPI
from features.auth import router as auth_router
from features.documents.router import router as docs_router
from features.documents import router as risk_router
app = FastAPI(title="LegalDocs API")

# Register routers
app.include_router(auth_router.router)
app.include_router(docs_router)
app.include_router(risk_router.router)

@app.get("/")
def root():
    return {"message": "Backend running ✅"}
