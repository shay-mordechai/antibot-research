import os
import google.generativeai as genai
from dotenv import load_dotenv

# עכשיו זה חסין תקלות!
load_dotenv(dotenv_path="config/.env", override=True)

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("[*] Fetching available models for your API Key...\n")

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f" - {m.name}")
except Exception as e:
    print(f"[-] Error: {e}")
