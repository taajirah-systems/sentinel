import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv('/Users/taajirah_systems/sentinel/.env')

api_key = os.getenv('TINY_FISH_API_KEY')

url = 'https://agent.tinyfish.ai/v1/automation/run-sse'
headers = {
    'X-API-Key': api_key,
    'Content-Type': 'application/json'
}

payload = {
    'url': 'https://www.google.com/search?q=site:tiktok.com+"luxury+event+planner"+OR+"wedding+planner"+"South+Africa"',
    'goal': 'Find 10 South African luxury event planners or wedding planners from the search results. Return their TikTok handles, names or company names, and their base city in South Africa if mentioned. Respond in JSON.'
}

print("Starting TinyFish request...")
try:
    response = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
    print(f"Status Code: {response.status_code}")
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            print(line_str)
            sys.stdout.flush()
            
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    if data.get('status') == 'completed':
                        print("\n\nCOMPLETED!")
                        print(json.dumps(data.get('output', {}), indent=2))
                        break
                    elif data.get('status') == 'failed':
                        print("\n\nFAILED!")
                        print(data.get('error'))
                        break
                except json.JSONDecodeError:
                    pass
except Exception as e:
    print(f"Error: {e}")
