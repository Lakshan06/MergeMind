from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
   allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Env variables
CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

# TEMP storage (later DB)
ACCESS_TOKEN = None


# 🔹 Root route
@app.get("/")
def home():
    return {"message": "MergeMind Backend Running 🚀"}


# 🔹 GitHub Login
@app.get("/auth/github")
def github_login():
    url = f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}&scope=repo"
    return RedirectResponse(url)


# 🔹 Callback
@app.get("/auth/github/callback")
def github_callback(code: str):
    global ACCESS_TOKEN

    token_res = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code
        },
        headers={"Accept": "application/json"}
    )

    ACCESS_TOKEN = token_res.json().get("access_token")

    return RedirectResponse("http://localhost:5173/dashboard")


# 🔹 Get repos
@app.get("/repos")
def get_repos():
    global ACCESS_TOKEN

    if not ACCESS_TOKEN:
        return []

    response = requests.get(
        "https://api.github.com/user/repos",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )

    return response.json()


# 🔹 Get PRs
@app.get("/prs/{owner}/{repo}")
def get_prs(owner: str, repo: str):
    global ACCESS_TOKEN

    if not ACCESS_TOKEN:
        return []

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )

    if response.status_code != 200:
        return []

    prs = response.json()

    if not isinstance(prs, list):
        return []

    detailed_prs = []

    for pr in prs:
        pr_details = requests.get(
            pr["url"],
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        ).json()

        detailed_prs.append({
            "title": pr.get("title"),
            "number": pr.get("number"),
            "mergeable": pr_details.get("mergeable"),
            "user": pr.get("user", {}).get("login")
        })

    return detailed_prs


# 🔹 Get PR files
@app.get("/pr-files/{owner}/{repo}/{pr_number}")
def get_pr_files(owner: str, repo: str, pr_number: int):
    global ACCESS_TOKEN

    if not ACCESS_TOKEN:
        return []

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"

    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )

    if response.status_code != 200:
        return []

    files = response.json()

    result = []

    for file in files:
        result.append({
            "filename": file.get("filename"),
            "status": file.get("status"),
            "patch": file.get("patch")
        })

    return result


# 🔹 AI Suggestion
@app.post("/ai-suggest")
def ai_suggest(data: dict):
    patch = data.get("patch", "")

    if not patch:
        return {"suggestion": "No changes found"}

    patch = patch[:1500]  # smaller = faster

    prompt = f"""
You are a senior software engineer.

Analyze this Git diff:

1. What changed
2. Risk level (Low / Medium / High)
3. Merge decision with reason

Diff:
{patch}
"""

    # ✅ OLLAMA (FIXED)
    try:
        print("🚀 Calling Ollama...")

        res = requests.post(
            "http://127.0.0.1:11434/api/generate",  # 🔥 USE 127.0.0.1 (IMPORTANT)
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=120  # 🔥 increase timeout
        )

        print("STATUS:", res.status_code)
        print("TEXT:", res.text[:300])

        if res.status_code == 200:
            result = res.json()

            if "response" in result:
                print("✅ OLLAMA SUCCESS")
                return {"suggestion": result["response"]}

        print("❌ Ollama bad response")

    except Exception as e:
        print("❌ Ollama failed:", str(e))

    # ✅ FALLBACK (only if Ollama REALLY fails)
    print("⚠️ USING FALLBACK")

    risk = "Low"
    decision = "Safe to merge"

    patch_lower = patch.lower()

    if "delete" in patch_lower or "remove" in patch_lower:
        risk = "Medium"
        decision = "Review before merging"

    if "auth" in patch_lower or "password" in patch_lower:
        risk = "High"
        decision = "Do NOT merge"

    return {
        "suggestion": f"""[Fallback]

Risk: {risk}
Decision: {decision}
"""
    }