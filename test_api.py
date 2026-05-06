import os
from mistralai.client import Mistral

API_KEY = "PTi82vsaj9TxFt0nak1S8vkdzySII73B"
if not API_KEY:
    print("❌ MISTRAL_API_KEY not set!")
    exit(1)

client = Mistral(api_key=API_KEY)

try:
    resp = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": "Say hello in one word"}],
    )
    print(f"Mistral says: {resp.choices[0].message.content.strip()}")
    print("✅ API is working!")
except Exception as e:
    print(f"❌ Error: {e}")
