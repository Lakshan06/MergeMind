import os
import requests
from dotenv import load_dotenv

load_dotenv()
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"
headers = {"Authorization": f"Bearer " + str(HF_API_KEY)}
prompt = "Analyze this Git diff:\n\n1. What changed\n2. Risk level (Low/Medium/High)\n3. Best merge decision\n\nDiff:\n+ print('hello')\n"

response = requests.post(
    API_URL,
    headers=headers,
    json={
        "inputs": prompt,
        "parameters": {"max_length": 200}
    }
)
print("STATUS:", response.status_code)
print("ERROR FULL:", response.text)
