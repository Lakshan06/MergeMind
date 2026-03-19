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
    allow_origins=["http://localhost:5174"],
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

    return RedirectResponse("http://localhost:5174/dashboard")


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

    if "<<<<<<<" in patch:
        suggestion = "⚠️ Conflict detected: Consider manual review"
    elif "+" in patch and "-" in patch:
        suggestion = "💡 Both sides modified: Try smart merge"
    elif "+" in patch:
        suggestion = "✅ Safe to take incoming changes"
    elif "-" in patch:
        suggestion = "⚡ Safe to keep existing code"
    else:
        suggestion = "🤖 No major changes detected"

    return {"suggestion": suggestion}