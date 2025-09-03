from fastapi import Depends, HTTPException, Header
from firebase_admin import auth

def get_current_user(authorization: str = Header(...)):
    """
    Verifies Firebase ID token from frontend request.
    Example: Authorization: Bearer <idToken>
    """
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header format")

        id_token = authorization.split(" ")[1]
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token  # contains uid, email, etc.
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token ❌")
