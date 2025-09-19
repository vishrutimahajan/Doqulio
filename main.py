import fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from features.auth import router as auth_router
from features.documents.router import router as docs_router
from features.chat.router import router as chat_router
from features.verification.router import router as verification_router
from features.Media.router import router as media_router

app = FastAPI(title="Docqulio Chatbot API")

# Define the origins that are allowed to make requests to this backend.
# In development, this will be your frontend's URL.
origins = [
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router.router)
app.include_router(docs_router)
app.include_router(chat_router)
app.include_router(verification_router)
app.include_router(media_router)


@app.get("/")
def root():
    return {"message": "Backend running ✅"}

@app.get("/test-integration")
def test_integration():
    """A simple endpoint to test that the frontend can connect to the backend."""
    return {"status": "success", "message": "Connection successful! Hello from FastAPI!"}
