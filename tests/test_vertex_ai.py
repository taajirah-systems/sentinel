import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai
import google.auth
from google.oauth2.credentials import Credentials as GoogleCredentials

def test_vertex_ai():
    load_dotenv()
    
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    
    print(f"--- Vertex AI Configuration ---")
    print(f"USE_VERTEX: {use_vertex}")
    print(f"PROJECT: {project}")
    print(f"LOCATION: {location}")
    
    if not use_vertex or not project or not location:
        print("❌ Vertex AI not fully configured in .env")
        return

    try:
        # Obtain credentials
        try:
            credentials, _ = google.auth.default()
            print("✅ Application Default Credentials found.")
        except Exception as e:
            print(f"⚠️ ADC failed: {e}")
            credentials = None

        # Fallback to OpenClaw token
        if not credentials or not hasattr(credentials, 'token') or not credentials.token:
            auth_path = Path.home() / ".openclaw" / "auth-profiles.json"
            if auth_path.exists():
                try:
                    auth_data = json.loads(auth_path.read_text())
                    profiles = auth_data.get("profiles", {})
                    for p_id, p_data in profiles.items():
                        if "google-antigravity" in p_id and p_data.get("access"):
                            credentials = GoogleCredentials(token=p_data["access"])
                            print(f"✅ Extracted OAuth token from OpenClaw profile: {p_id}")
                            break
                except Exception as e:
                    print(f"⚠️ Failed to parse OpenClaw tokens: {e}")

        if not credentials:
            print("❌ No valid credentials found.")
            return

        client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
            credentials=credentials
        )
        
        print("🚀 Sending test request to google/gemini-3.1-flash-lite-preview...")
        response = client.models.generate_content(
            model="google/gemini-3.1-flash-lite-preview",
            contents="Say 'Vertex AI is active!'"
        )
        print(f"✨ Response: {response.text}")
        print("✅ Vertex AI API is ENABLED and TESTED.")

    except Exception as e:
        print(f"❌ Vertex AI Test Failed: {e}")
        if "403" in str(e) or "PermissionDenied" in str(e):
            print("💡 Hint: Ensure Vertex AI API is enabled at https://console.cloud.google.com/apis/library/aiplatform.googleapis.com")

if __name__ == "__main__":
    test_vertex_ai()
