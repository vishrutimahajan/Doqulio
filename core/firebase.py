import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Get path from env
cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT")

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()
