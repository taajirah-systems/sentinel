import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
client = genai.Client(api_key=api_key)

print(f"Listing models for API Key: {api_key[:10]}...")
try:
    for model in client.models.list():
        print(f"- {model.name}")
except Exception as e:
    print(f"Error listing models: {e}")
