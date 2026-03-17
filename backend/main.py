from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

# TEMP storage (later we use DB)
ACCESS_TOKEN = None

# Step 1: Login
@app.get("/auth/github")
def github_login():
    url = f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}&scope=repo"
    return RedirectResponse(url)

# Step 2: Callback
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

    # redirect back to frontend
    return RedirectResponse("http://localhost:5174/dashboard")

# Step 3: Get repos
@app.get("/repos")
def get_repos():
    global ACCESS_TOKEN

    repos = requests.get(
        "https://api.github.com/user/repos",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    ).json()

    return repos