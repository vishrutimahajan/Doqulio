import datetime
from firebase_admin import firestore
import google.generativeai as genai
from core.firebase import db

# Now you can do
# db.collection("chat_history").document(user_id).set(...)
# and use genai for AI interactions
db = firestore.client()
genai.configure(api_key="YOUR_GEMINI_API_KEY")

def get_ai_response(user_id: str, question: str) -> str:
    model = genai.GenerativeModel("gemini-1.0-pro")
    response = model.generate_content(
        f"You are a helpful legal assistant. Answer this: {question}",
        generation_config={"max_output_tokens": 500}
    )
    answer = response.text.strip()

    doc_ref = db.collection("chat_history").document(user_id)
    doc_ref.set({
        "chats": firestore.ArrayUnion([{
            "question": question,
            "answer": answer,
            "timestamp": datetime.datetime.utcnow()
        }])
    }, merge=True)

    return answer