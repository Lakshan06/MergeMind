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
# 🚀 APPLY MERGE (SIMULATION)
# -----------------------------
@app.post("/apply-merge")
def apply_merge(data: dict):
    owner = data.get("owner")
    repo = data.get("repo")
    prs = data.get("prs", [])
    result = data.get("result")

    print("✅ APPLY MERGE CALLED")
    print("PRs:", prs)

    if not result:
        return {"status": "error", "message": "No merge result provided"}

    return {
        "status": "success",
        "message": f"✅ Merge applied successfully for PRs {prs}"
    }


# -----------------------------
# 🔥 SMART MERGE (REAL AI UPGRADE)
# -----------------------------
@app.post("/smart-merge")
def smart_merge(data: dict):
    owner = data.get("owner")
    repo = data.get("repo")
    prs = data.get("prs", [])

    if not prs or len(prs) < 2:
        return {"result": "❌ Select at least 2 PRs"}

    try:
        print("🚀 Fetching PR data:", prs)

        file_changes = {}

        for pr in prs:
            res = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr}/files",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
            )

            if res.status_code != 200:
                continue

            files = res.json()

            for f in files:
                filename = f.get("filename")
                if not filename:
                    continue

                content = ""

                # 🔥 Try raw file
                raw_url = f.get("raw_url")
                if raw_url:
                    try:
                        raw_res = requests.get(raw_url, timeout=5)
                        if raw_res.status_code == 200:
                            content = raw_res.text[:800]
                    except:
                        pass

                # 🔥 fallback patch
                if not content:
                    patch = f.get("patch")
                    if patch:
                        content = patch[:500]

                # 🔥 always keep something
                if not content:
                    content = f"// No diff available for {filename}"

                if filename not in file_changes:
                    file_changes[filename] = []

                file_changes[filename].append({
                    "pr": pr,
                    "content": content
                })

        # 🔥 fallback if empty
        if not file_changes:
            return {"result": "⚠ No strong code found, try smaller PRs"}

        structured_input = ""

        for file, changes in file_changes.items():
            structured_input += f"\n\n### FILE: {file}\n"
            for c in changes:
                structured_input += f"\n--- PR #{c['pr']} ---\n{c['content']}\n"

        prompt = f"""
You are a senior engineer merging PRs safely.

Rules:
- Keep working code
- Remove duplicates
- Prefer latest logic
- Keep minimal changes
- If unsure → choose safest version

Respond EXACTLY:

### Merged Files
- list files

### Final Merged Code
<code>

### Conflict Resolution
- explain

### Developer Notes
- what to test

INPUT:
{structured_input}
"""

        try:
            res = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120   # 🔥 reduced timeout (better UX)
            )

            if res.status_code != 200:
                return {"result": "❌ AI service error"}

            output = res.json().get("response", "").strip()

            if not output:
                return {"result": "⚠ AI returned empty result"}

            return {"result": output}

        except requests.exceptions.Timeout:
            # 🔥 CRITICAL FIX → NO HARD FAIL
            return {
                "result": """### Merged Files
- fallback

### Final Merged Code
// AI timeout → manual review required

### Conflict Resolution
- AI timeout

### Developer Notes
- retry or merge manually
"""
            }

        except Exception as e:
            return {"result": f"❌ AI error: {str(e)}"}

    except Exception as e:
        return {"result": f"❌ Error: {str(e)}"}


# -----------------------------
# 🟢 MERGE READY AI (FINAL + DEBUG + FALLBACK)
# -----------------------------
@app.post("/merge-ready")
def merge_ready(data: dict):
    owner = data.get("owner")
    repo = data.get("repo")

    try:
        print("🚀 Fetching PRs...")

        res = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )

        if res.status_code != 200:
            print("❌ GitHub API error:", res.status_code)
            return {"result": "❌ Failed to fetch PRs"}

        prs = res.json()

        if not prs:
            return {"result": "No PRs found"}

        ready = []
        risky = []
        conflict = []

        summary_for_ai = ""

        # 🔥 Analyze PRs
        for pr in prs[:6]:
            detail = requests.get(
                pr["url"],
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
            ).json()

            state = detail.get("mergeable_state")

            info = f"PR #{pr['number']}: {pr['title']} ({state})\n"
            summary_for_ai += info

            if state == "clean":
                ready.append(pr["number"])
            elif state in ["dirty", "conflicting"]:
                conflict.append(pr["number"])
            else:
                risky.append(pr["number"])

        print("📊 READY:", ready)
        print("⚠️ RISKY:", risky)
        print("❌ CONFLICT:", conflict)

        # -----------------------------
        # 🤖 AI PART (WITH DEBUG)
        # -----------------------------
        prompt = f"""
You are a senior software engineer.

Analyze pull requests based on mergeability.

Respond EXACTLY:

### Ready to Merge
- list PR numbers

### Risky PRs
- list PR numbers

### Conflicts
- list PR numbers

### Final Recommendation
- what should developer do

PR Data:
{summary_for_ai}
"""

        ai_output = ""

        try:
            print("🚀 Sending to Ollama...")

            ai_res = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=90
            )

            print("📡 Ollama status:", ai_res.status_code)

            if ai_res.status_code == 200:
                data_ai = ai_res.json()
                ai_output = data_ai.get("response", "").strip()

                if ai_output:
                    print("✅ AI SUCCESS")
                else:
                    print("⚠️ Empty AI response")

            else:
                print("❌ Ollama bad status")

        except requests.exceptions.Timeout:
            print("⏳ AI TIMEOUT")

        except Exception as e:
            print("🔥 AI ERROR:", str(e))

        # -----------------------------
        # 🧠 FALLBACK (VERY IMPORTANT)
        # -----------------------------
        if not ai_output:
            print("⚠️ USING FALLBACK AI")

            ai_output = f"""
### Ready to Merge
{', '.join([f'PR #{p}' for p in ready]) or 'None'}

### Risky PRs
{', '.join([f'PR #{p}' for p in risky]) or 'None'}

### Conflicts
{', '.join([f'PR #{p}' for p in conflict]) or 'None'}

### Final Recommendation
- Merge READY PRs first
- Review RISKY PRs carefully
- Fix conflicts before merging
"""

        # -----------------------------
        # ✅ FINAL RESPONSE
        # -----------------------------
        return {
            "ready": ready,
            "risky": risky,
            "conflict": conflict,
            "ai": ai_output
        }

    except Exception as e:
        print("🔥 MERGE READY ERROR:", str(e))
        return {"result": "❌ MergeReady failed"}