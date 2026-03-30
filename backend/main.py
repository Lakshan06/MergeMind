from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

ACCESS_TOKEN = None


# -----------------------------
# ROOT
# -----------------------------
@app.get("/")
def home():
    return {"message": "MergeMind Backend Running 🚀"}


# -----------------------------
# AUTH
# -----------------------------
@app.get("/auth/github")
def github_login():
    url = f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}&scope=repo"
    return RedirectResponse(url)


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


# -----------------------------
# REPOS
# -----------------------------
@app.get("/repos")
def get_repos():
    if not ACCESS_TOKEN:
        return []

    res = requests.get(
        "https://api.github.com/user/repos",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )

    return res.json()


# -----------------------------
# PRs
# -----------------------------
@app.get("/prs/{owner}/{repo}")
def get_prs(owner: str, repo: str):
    if not ACCESS_TOKEN:
        return []

    res = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/pulls",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )

    prs = res.json()

    result = []
    for pr in prs:
        detail = requests.get(
            pr["url"],
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        ).json()

        result.append({
            "title": pr["title"],
            "number": pr["number"],
            "mergeable": detail.get("mergeable"),
            "user": pr["user"]["login"]
        })

    return result


# -----------------------------
# PR FILES
# -----------------------------
@app.get("/pr-files/{owner}/{repo}/{pr_number}")
def get_pr_files(owner: str, repo: str, pr_number: int):
    if not ACCESS_TOKEN:
        return []

    res = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )

    return [
        {
            "filename": f["filename"],
            "status": f["status"],
            "patch": f.get("patch")
        }
        for f in res.json()
    ]



# 🔹 AI Suggestion
@app.post("/ai-suggest")
def ai_suggest(data: dict):
    patch = data.get("patch", "")

    if not patch:
        return {"suggestion": "No changes found"}

    patch = patch[:1500]  # smaller = faster

    prompt =  f"""
You are a senior software engineer reviewing a GitHub pull request.

Explain the changes clearly in simple English.

Respond EXACTLY in this format:

### What Changed
- point
- point

### Risk Level
Low / Medium / High

### Explanation
Explain the risk in 1-2 lines

### Merge Decision
Approve / Review / Reject

### Reason
Short reason

Keep it clean, do not repeat sections.

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



# -----------------------------
# 🔥 SMART MERGE (MULTI PR FINAL)
# -----------------------------
@app.post("/smart-merge")
def smart_merge(data: dict):
    owner = data.get("owner")
    repo = data.get("repo")
    pr = data.get("pr")

    if not pr:
        return {"result": "❌ No PR selected"}

    try:
        print("🚀 Fetching PR files...")

        res = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr}/files",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )

        if res.status_code != 200:
            print("❌ GitHub API failed:", res.status_code)
            return {"result": "❌ Failed to fetch PR files"}

        files = res.json()

        patches = []
        file_names = []

        # ✅ LIMIT DATA (PERFORMANCE FIX)
        for f in files[:3]:
            if f.get("patch"):
                patches.append(f["patch"][:400])
                file_names.append(f["filename"])

        if not patches:
            return {"result": "❌ No code changes found"}

        combined = "\n\n".join(patches)

        print("📂 Files used:", file_names)
        print("🚀 Sending to Ollama...")

        prompt = f"""
You are a senior software engineer.

Analyze this pull request with multiple file changes.

Your job:
- Understand all changes
- Improve code quality
- Remove issues
- Generate FINAL CLEAN VERSION

Respond EXACTLY:

### Summary
- what changed
- what improved

### Final Code
<clean improved code>

### Why This Is Better
- reason
- reason

Files:
{file_names}

Code:
{combined}
"""

        # 🔥 OLLAMA CALL (STRONG FIX)
        try:
            res = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=180
            )

            print("📡 Ollama status:", res.status_code)

            if res.status_code != 200:
                return {"result": "❌ Ollama API error"}

            data = res.json()

            # ✅ SAFE RESPONSE HANDLING
            output = data.get("response", "").strip()

            if not output:
                return {"result": "❌ Empty AI response"}

            print("✅ AI RESPONSE RECEIVED")

            return {"result": output}

        except requests.exceptions.Timeout:
            print("⏳ Ollama Timeout")
            return {"result": "❌ AI timeout (model too slow)"}

        except Exception as e:
            print("🔥 Ollama Error:", str(e))
            return {"result": f"❌ Ollama error: {str(e)}"}

    except Exception as e:
        print("🔥 SMART MERGE ERROR:", str(e))
        return {"result": f"❌ Error: {str(e)}"}

# -----------------------------
# 🔥 BEST PR (AI BASED FIX)
# -----------------------------
@app.post("/best-pr")
def best_pr(data: dict):
    owner = data.get("owner")
    repo = data.get("repo")

    res = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/pulls",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )

    prs = res.json()

    if not prs:
        return {"best_pr": None}

    summary = ""
    for pr in prs[:5]:  # 🔥 LIMIT
        summary += f"PR #{pr['number']}: {pr['title']}\n"

    prompt = f"""
Choose the best pull request to merge.

Criteria:
- Stability
- Simplicity
- Low risk

PRs:
{summary}

Answer ONLY like:
Best PR: <number>
"""

    try:
        res = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=25
        )

        output = res.json().get("response", "")

        # 🔥 EXTRACT NUMBER
        import re
        match = re.search(r"\d+", output)

        if match:
            return {"best_pr": int(match.group())}

    except Exception as e:
        print("BEST PR ERROR:", e)

    # fallback
    return {"best_pr": prs[0]["number"]}