import firebase_admin
from firebase_admin import auth, credentials
from fastapi import HTTPException

# --- Firebase Initialization ---
FIREBASE_KEY = "C:/Users/Vishruti/.credentials/service-account.json"

if not firebase_admin._apps:  # prevents re-init errors on reload
    cred = credentials.Certificate(FIREBASE_KEY)
    firebase_admin.initialize_app(cred)


# --- Firebase Auth Token Verification ---
def verify_token(id_token: str):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token["uid"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
