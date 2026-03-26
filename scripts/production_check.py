import os
import json
import sys

def check_env():
    print("[*] Auditing Production Credentials...")
    
    # Check Firebase
    fb_path = "/Users/taajirah_systems/taajirah_systems/.credentials/firebase-service-account.json"
    if os.path.exists(fb_path):
        print(f"[+] Firebase Service Account Key: FOUND ({fb_path})")
    else:
        print(f"[-] Firebase Service Account Key: MISSING ({fb_path})")
        return False

    # Check TinyFish
    with open("/Users/taajirah_systems/sentinel/.env", "r") as f:
        env_content = f.read()
        if "TINY_FISH_API_KEY" in env_content:
            print("[+] TinyFish API Key: FOUND in sentinel/.env")
        else:
            print("[-] TinyFish API Key: MISSING in sentinel/.env")
            return False

    # Check Gemini
    if "GEMINI_API_KEY" in env_content:
        print("[+] Gemini API Key: FOUND in sentinel/.env")
    else:
        print("[-] Gemini API Key: MISSING in sentinel/.env")
        return False

    print("[!] PRODUCTION READINESS: VERIFIED")
    return True

if __name__ == "__main__":
    if not check_env():
        sys.exit(1)
    sys.exit(0)
