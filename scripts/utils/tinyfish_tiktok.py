import os
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
    'url': 'https://www.tiktok.com/search?q=south%20african%20luxury%20event%20planner',
    'goal': 'Find 10 South African luxury event planners or wedding planners from the search results. Return their TikTok handles, names or company names, and their base city in South Africa if mentioned. Respond in JSON.'
}

response = requests.post(url, headers=headers, json=payload, stream=True)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
