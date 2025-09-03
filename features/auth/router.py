from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .schemas import SignUpRequest, AuthResponse
from .service import create_user, get_custom_token
from firebase_admin import auth

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    id_token: str


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignUpRequest):
    try:
        user = create_user(payload.email, payload.password)
        token = get_custom_token(user.uid)
        return AuthResponse(uid=user.uid, email=user.email, token=token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(payload: LoginRequest):
    """
    Verifies the Firebase ID token from frontend.
    Frontend should call Firebase.auth().signInWithEmailAndPassword
    to get this idToken and send it here.
    """
    try:
        decoded_token = auth.verify_id_token(payload.id_token)
        uid = decoded_token["uid"]
        email = decoded_token.get("email")
        return {"msg": "User authenticated ✅", "uid": uid, "email": email}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token ❌")
