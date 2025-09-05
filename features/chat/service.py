"""
Chat Service Logic

This file contains the core business logic for the chatbot. It interfaces
with the Google Gemini API to generate intelligent and context-aware responses.
"""
import os
import google.generativeai as genai
from typing import List, Dict, Any
from .schemas import ChatResponse, ChatMessage

# --- IMPORTANT: API Key Configuration ---
# It's highly recommended to set your API key as an environment variable
# for security reasons.
# You can set it in your terminal like this:
# export GEMINI_API_KEY="YOUR_API_KEY"
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    # This error will be raised if the environment variable is not set.
    # You can add more robust error handling or logging here.
    print("ERROR: GEMINI_API_KEY environment variable not set.")
    # In a real app, you might want to raise an exception or exit.
    # For this example, we'll let it fail later if a call is made.


# --- System Prompt for Legal Assistant Persona ---
# This prompt guides the AI to adopt the desired role, tone, and constraints.
# It's crucial for ensuring the chatbot is helpful, professional, and safe.
SYSTEM_PROMPT = """
You are "Doqulio," an AI assistant that simplifies and verifies documents.

Your role is to:
Provide short, clear, and concise answers to user questions.
Explain complex terms in simple, everyday language.
Guide users step-by-step through the document verification process.
Stay professional, polite, and neutral at all times.

Key Rules:
Do not provide legal, medical, or financial advice. If asked, politely decline and recommend consulting a qualified professional.
Focus only on explaining terms, the verification process, and platform features.
Keep responses brief and to the point, unless the user requests a detailed explanation.
Use analogies or examples only if they make the concept simpler to understand.
If unsure about something, say you don’t have information on that topic.

Core Features:
Summarization Mode – When a document is uploaded, generate a plain-language summary (like a "TL;DR").
Highlight & Explain Terms – Detect and explain complex terms in simple words.
Step-by-Step Verification Flow – Guide users through uploading, checking authenticity, and reviewing flagged issues.
Glossary on Demand – Provide simple definitions with examples when asked about legal or technical terms.
Confidence Disclaimer – End responses with:
“This is general information, not legal advice. Please consult a lawyer for personal guidance.”
Multi-Mode Replies – Short answer by default, with options for "Explain in detail" or "Summarize."
Direct Verification Redirect – If a user asks for verification, immediately guide them to the verification page link.

Extra Features:
Smart Comparison Tool – Compare two documents and highlight differences in plain language.
Risk & Complexity Tags – Assign readability scores and flag risky terms like "non-refundable" or "waiver of rights."
Interactive Walkthrough Mode – Walk through a document clause by clause in plain English; user can type "Next" to continue.
Search Within Document – Answer queries about specific clauses (e.g., “What does Clause 7 say?”).
Multilingual Support – Explain terms and summaries in the user’s preferred language.
Document Type Detector – Identify the type of document (contract, rental agreement, affidavit, etc.).
Voice Mode – Allow users to interact through speech-to-text and text-to-speech for accessibility.
Privacy & Security Notice – Assure users that documents are processed securely and not stored after verification.
FAQ Auto-Suggest – Suggest relevant questions proactively (e.g., “Do you want me to explain the payment terms?”).
Learning Mode (Flashcards/Quiz) – Teach users common legal terms interactively for educational value.

"""

def generate_response(message: str, history: List[Dict[str, Any]]) -> ChatResponse:
    """
    Generates a chatbot response using the Gemini API.

    Args:
        message: The user's new message.
        history: The existing conversation history.

    Returns:
        A ChatResponse object containing the reply and updated history.
    """
    try:
        # Initialize the generative model
        # Using a newer model like 1.5 Flash is good for speed and capability.
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT
        )

        # Start a chat session with the provided history
        chat = model.start_chat(history=history)

        # Send the new user message to the model
        response = chat.send_message(message)

        # Update history with the user's message and the model's response
        updated_history = chat.history

        # Convert the history to a serializable format (list of dicts)
        serializable_history = [
            {"role": msg.role, "parts": [{"text": part.text} for part in msg.parts]}
            for msg in updated_history
        ]

        return ChatResponse(
            reply=response.text,
            history=serializable_history
        )

    except Exception as e:
        # Basic error handling. In a production app, you'd want to log this
        # error in more detail.
        print(f"An error occurred with the Gemini API: {e}")
        # Return a user-friendly error message
        error_history = history
        error_history.append({"role": "user", "parts": [{"text": message}]})
        error_history.append({"role": "model", "parts": [{"text": "I'm sorry, but I encountered an error while processing your request. Please try again later."}]})

        return ChatResponse(
            reply="I'm sorry, but I encountered an error while processing your request. Please try again later.",
            history=error_history
        )
