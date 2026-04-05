"""
HuggingFace API diagnostic test for MergeMind.
Run with:  python test_hf.py   (from backend folder, with venv active)
"""
import os
import requests
from dotenv import load_dotenv

# Force re-read .env even if already loaded
load_dotenv(override=True)

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "").strip()

print("=" * 60)
print("MergeMind — HuggingFace API Test")
print("=" * 60)

if not HF_API_KEY or HF_API_KEY == "your_hf_token_here":
    print()
    print("❌  HUGGINGFACE_API_KEY is missing or not set!")
    print()
    print("  The .env file currently has the placeholder value.")
    print("  You need to replace it with your real token.")
    print()
    print("  Steps:")
    print("  1. Go to: https://huggingface.co/settings/tokens")
    print("  2. Click 'New token' → Type: Read → Create")
    print("  3. Copy your token (starts with hf_...)")
    print("  4. Open backend/.env and change line 5 to:")
    print("       HUGGINGFACE_API_KEY=hf_YOUR_ACTUAL_TOKEN")
    print("  5. Save the file and re-run this test.")
    print()
    exit(1)

print(f"\n✅  Key loaded: {HF_API_KEY[:12]}{'*' * 8}")
print()

MODELS = [
    "mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFaceH4/zephyr-7b-beta",
    "microsoft/Phi-3-mini-4k-instruct",
]

working_model = None

for model in MODELS:
    url = f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions"
    print(f"→  Testing: {model}")
    try:
        res = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {HF_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "In one sentence, what does a Python print() statement do?"}],
                "max_tokens": 50,
                "temperature": 0.3,
                "stream": False
            },
            timeout=45
        )

        print(f"   Status: {res.status_code}")

        if res.status_code == 200:
            data = res.json()
            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if text:
                print(f"   ✅  WORKS! → {text[:120]}")
                working_model = model
                break
            else:
                print("   ⚠️  Empty response — trying next model")

        elif res.status_code == 401:
            print("   ❌  Invalid API key — the token you pasted may be wrong")
            print("       Make sure it starts with 'hf_' and you saved the .env file")
            break

        elif res.status_code == 503:
            print("   ⏳  Model warming up — will auto-retry in production, trying next")

        else:
            print(f"   ❌  Unexpected error: {res.text[:200]}")

    except requests.exceptions.Timeout:
        print("   ⏳  Timeout (free tier cold start) — trying next model")
    except Exception as e:
        print(f"   ❌  Exception: {e}")

print()
print("=" * 60)
if working_model:
    print(f"✅  AI is WORKING with: {working_model}")
    print("   Smart Merge will use this model automatically.")
    print("   No restart needed — uvicorn will pick up the key.")
else:
    print("❌  No model responded successfully.")
    print("   → Make sure the API key in .env starts with 'hf_'")
    print("   → Try again in ~30s (models warm up on first call)")
print("=" * 60)
