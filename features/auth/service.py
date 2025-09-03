# backend/features/auth/service.py
from firebase_admin import auth
import firebase_admin

def create_user(email: str, password: str):
    user = auth.create_user(
        email=email,
        password=password
    )
    return user
def get_custom_token(uid: str):
    token = auth.create_custom_token(uid)
    return token.decode("utf-8")

# Verify Firebase ID token
def verify_id_token(id_token: str):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token  # contains uid, email, etc.
    except Exception as e:
        raise ValueError(f"Invalid token: {str(e)}")