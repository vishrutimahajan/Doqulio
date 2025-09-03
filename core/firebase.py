import firebase_admin
from firebase_admin import credentials, auth, firestore

# Only initialize once
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/Users/Vishruti/.credentials/service-account.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
