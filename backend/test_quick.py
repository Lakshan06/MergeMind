import os, requests
from dotenv import load_dotenv

load_dotenv(override=True)
key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
print("KEY:", key[:15], "...")

url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3/v1/chat/completions"

try:
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "mistralai/Mistral-7B-Instruct-v0.3",
            "messages": [{"role": "user", "content": "Say hello in one word"}],
            "max_tokens": 10,
            "stream": False
        },
        timeout=45
    )
    print("STATUS:", r.status_code)
    print("RESPONSE:", r.text[:500])
except Exception as e:
    print("ERROR:", e)

# Try zephyr too
url2 = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta/v1/chat/completions"
try:
    r2 = requests.post(
        url2,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "HuggingFaceH4/zephyr-7b-beta",
            "messages": [{"role": "user", "content": "Say hello in one word"}],
            "max_tokens": 10,
            "stream": False
        },
        timeout=45
    )
    print("ZEPHYR STATUS:", r2.status_code)
    print("ZEPHYR RESPONSE:", r2.text[:500])
except Exception as e:
    print("ZEPHYR ERROR:", e)
