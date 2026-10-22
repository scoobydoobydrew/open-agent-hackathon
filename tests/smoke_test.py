import os
import requests
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {NVIDIA_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
    "messages": [
        {"role": "user", "content": "What is the primary biological function of the p53 gene? Keep it to one short sentence."}
    ],
    "max_tokens": 1024,  # Αυξήσαμε το όριο για να προλάβει να σκεφτεί και να απαντήσει
    "temperature": 0.2
}

print("Στέλνω request στο NVIDIA Nemotron...\n")

try:
    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status() 
    
    data = response.json()
    message = data["choices"][0]["message"]
    
    print("🧠 Εσωτερική Σκέψη Μοντέλου (Reasoning):")
    print(message.get("reasoning_content"))
    
    print("\n✅ Τελική Απάντηση (Content):")
    print(message.get("content"))
    
except Exception as e:
    print("\n❌ Σφάλμα σύνδεσης:", e)