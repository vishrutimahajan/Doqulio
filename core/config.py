import os
from dotenv import load_dotenv

load_dotenv()  # load .env file

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")