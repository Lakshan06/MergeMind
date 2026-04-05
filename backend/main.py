from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import base64
import time
import re
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
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

ACCESS_TOKEN = None

# HuggingFace Router API (new endpoint — OpenAI-compatible)
# Old api-inference.huggingface.co returns 410 Gone; use router.huggingface.co instead
HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODELS = [
    "meta-llama/Meta-Llama-3-8B-Instruct",      # Primary  — fast, free tier
    "mistralai/Mistral-7B-Instruct-v0.3",        # Fallback 1
    "HuggingFaceH4/zephyr-7b-beta",              # Fallback 2
]


# -----------------------------
# 🤖 SHARED AI HELPER
# -----------------------------
def call_ai(prompt: str, max_tokens: int = 512) -> str:
    """
    Call HuggingFace Router API (OpenAI-compatible Chat Completions).
    Tries each model in HF_MODELS until one succeeds.
    Returns the AI text response, or empty string if all models fail.
    """
    # Re-read from environment every call so uvicorn --reload picks up .env changes
    load_dotenv(override=True)
    hf_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()

    if not hf_key or hf_key in ("your_hf_token_here", ""):
        print("⚠️  HUGGINGFACE_API_KEY not set — please add it to backend/.env")
        print("   Get a free key at: https://huggingface.co/settings/tokens")
        return ""

    for model in HF_MODELS:
        try:
            print(f"🚀 Calling HuggingFace ({model})...")
            res = requests.post(
                HF_ROUTER_URL,
                headers={
                    "Authorization": f"Bearer {hf_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt.strip()}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                    "stream": False
                },
                timeout=60
            )

            print(f"📡 HF status ({model}):", res.status_code)

            if res.status_code == 200:
                data = res.json()
                text = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                if text:
                    print("✅ AI SUCCESS via", model)
                    return text
                print("⚠️  Empty response from", model)

            elif res.status_code == 401:
                print("❌ Invalid HuggingFace API key — check HUGGINGFACE_API_KEY in .env")
                return ""  # Don't retry other models if key is wrong

            elif res.status_code == 503:
                print(f"⏳ Model {model} loading, trying next...")

            else:
                print(f"❌ HF bad response from {model}:", res.text[:200])

        except requests.exceptions.Timeout:
            print(f"⏳ HF timeout on {model}, trying next...")
        except Exception as e:
            print(f"🔥 HF error on {model}:", str(e))

    print("❌ All AI models failed — using fallback")
    return ""


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

    patch = patch[:2000]

    prompt = f"""You are a senior software engineer reviewing a GitHub pull request diff.
Analyze the diff below and respond EXACTLY in this format (no extra text):

### What Changed
- bullet point
- bullet point

### Risk Level
Low / Medium / High

### Explanation
Explain the risk in 1-2 lines.

### Merge Decision
Approve / Review / Reject

### Reason
One short sentence.

Diff:
{patch}"""

    ai_text = call_ai(prompt, max_tokens=400)

    if ai_text:
        return {"suggestion": ai_text}

    # Smart keyword-based fallback
    print("⚠️ USING KEYWORD FALLBACK")
    patch_lower = patch.lower()
    risk = "Low"
    decision = "Approve"
    reason = "Minor changes with no obvious risk"

    if any(w in patch_lower for w in ["delete", "remove", "drop table", "rm -rf"]):
        risk = "Medium"
        decision = "Review"
        reason = "Deletion or removal detected — verify intent"

    if any(w in patch_lower for w in ["auth", "password", "token", "secret", "api_key", "private"]):
        risk = "High"
        decision = "Reject"
        reason = "Sensitive credential or auth change — manual review required"

    added = sum(1 for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in patch.splitlines() if l.startswith("-") and not l.startswith("---"))

    return {
        "suggestion": f"""### What Changed
- {added} line(s) added, {removed} line(s) removed
- Keyword analysis applied (AI unavailable)

### Risk Level
{risk}

### Explanation
{reason}

### Merge Decision
{decision}

### Reason
{reason}
"""
    }


# -----------------------------
# 🚀 APPLY MERGE — Real GitHub PR Creation
# -----------------------------

@app.post("/apply-merge")
def apply_merge(data: dict):
    owner        = data.get("owner")
    repo         = data.get("repo")
    prs          = data.get("prs", [])
    merged_files = data.get("merged_files", {})  # {filename: merged_code_string}

    print("APPLY MERGE CALLED | PRs:", prs, "| Files:", list(merged_files.keys()))

    if not merged_files:
        return {"status": "error", "message": "❌ No merged files provided"}
    if not ACCESS_TOKEN:
        return {"status": "error", "message": "❌ Not authenticated — please login first"}

    gh = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/vnd.github+json"}

    try:
        # ─────────────────────────────────────
        # 1. Get repo default branch
        # ─────────────────────────────────────
        repo_res = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}", headers=gh
        )
        if repo_res.status_code != 200:
            return {"status": "error", "message": f"❌ Could not fetch repo info: {repo_res.status_code}"}

        default_branch = repo_res.json().get("default_branch", "main")
        print(f"  ℹ️  Default branch: {default_branch}")

        # ─────────────────────────────────────
        # 2. Get default branch HEAD SHA
        # ─────────────────────────────────────
        ref_res = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{default_branch}",
            headers=gh
        )
        if ref_res.status_code != 200:
            return {"status": "error", "message": f"❌ Could not get branch SHA: {ref_res.text[:200]}"}

        base_sha = ref_res.json()["object"]["sha"]
        print(f"  ℹ️  Base SHA: {base_sha[:10]}...")

        # ─────────────────────────────────────
        # 3. Create a new branch: mergemind/merge-<prs>-<ts>
        # ─────────────────────────────────────
        pr_slug  = "-".join(str(p) for p in prs)
        ts       = int(time.time())
        branch   = f"mergemind/merge-pr{pr_slug}-{ts}"

        br_res = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/git/refs",
            headers=gh,
            json={"ref": f"refs/heads/{branch}", "sha": base_sha}
        )
        if br_res.status_code not in (200, 201):
            return {"status": "error", "message": f"❌ Could not create branch '{branch}': {br_res.text[:300]}"}

        print(f"  ✅ Branch created: {branch}")

        # ─────────────────────────────────────
        # 4. Commit each merged file onto the new branch
        # ─────────────────────────────────────
        committed = []
        for filename, code in merged_files.items():
            # Get current file SHA on the new branch (needed for update, not for new files)
            file_res = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{filename}",
                headers=gh,
                params={"ref": branch}
            )
            file_sha = file_res.json().get("sha") if file_res.status_code == 200 else None

            content_b64 = base64.b64encode(code.encode("utf-8")).decode("utf-8")
            pr_labels = ", ".join(f"#{p}" for p in prs)

            put_payload = {
                "message": f"MergeMind: merge {filename} from PR {pr_labels}",
                "content": content_b64,
                "branch": branch
            }
            if file_sha:
                put_payload["sha"] = file_sha

            put_res = requests.put(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{filename}",
                headers=gh,
                json=put_payload
            )

            if put_res.status_code in (200, 201):
                print(f"  ✅ Committed: {filename}")
                committed.append(filename)
            else:
                print(f"  ⚠️  Could not commit {filename}: {put_res.text[:200]}")

        if not committed:
            return {"status": "error", "message": "❌ No files could be committed to the branch"}

        # ─────────────────────────────────────
        # 5. Open real Pull Request
        # ─────────────────────────────────────
        pr_labels_md = "\n".join(f"- PR #{p}" for p in prs)
        files_md     = "\n".join(f"- `{f}`" for f in committed)

        pr_body = f"""## 🤖 MergeMind — AI Smart Merge

This pull request was automatically created by **MergeMind** by intelligently merging:

{pr_labels_md}

### Files merged
{files_md}

### How it was done
- Full file content fetched from each PR’s head branch
- AI (LLaMA-3-8B via HuggingFace) performed 3-way intelligent merge
- All conflicts auto-resolved by AI
- Branch: `{branch}`

*Generated by [MergeMind](https://github.com) AI Merge Engine*
"""

        pr_title = f"🤖 MergeMind: Smart Merge of PR {pr_labels}"

        pr_res = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers=gh,
            json={
                "title": pr_title,
                "body":  pr_body,
                "head":  branch,
                "base":  default_branch
            }
        )

        if pr_res.status_code in (200, 201):
            pr_data = pr_res.json()
            pr_url  = pr_data["html_url"]
            pr_num  = pr_data["number"]
            print(f"  ✅ PR #{pr_num} created: {pr_url}")
            return {
                "status":     "success",
                "pr_url":     pr_url,
                "pr_number":  pr_num,
                "branch":     branch,
                "committed":  committed,
                "message":    f"✅ PR #{pr_num} created successfully!"
            }

        return {"status": "error", "message": f"❌ PR creation failed: {pr_res.text[:300]}"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}



# -----------------------------
# 🔥 SMART MERGE — AI-First 3-Way Merge
# -----------------------------


def _get_file_at_ref(owner: str, repo: str, filename: str, ref: str) -> str:
    """Fetch full file content from GitHub at a specific branch/SHA ref. Returns text or ''."""
    try:
        res = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{filename}",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            params={"ref": ref}
        )
        if res.status_code == 200:
            raw = res.json().get("content", "")
            return base64.b64decode(raw).decode("utf-8", errors="replace")
        if res.status_code == 404:
            return ""   # File doesn't exist at this ref (new file in PR)
    except Exception as e:
        print(f"  ⚠️  fetch_file({filename}@{ref}): {e}")
    return ""


def _ext(filename: str) -> str:
    """Return file extension for fenced code blocks."""
    return filename.rsplit(".", 1)[-1] if "." in filename else ""


def _ai_merge_file(filename: str, base: str, pr_versions: dict, pr_info: dict) -> dict:
    """
    Ask AI to perform a full intelligent 3-way merge of a single file.
    Returns {"merged_code": str, "explanation": str}
    """
    lang = _ext(filename)

    # Build the versions section of the prompt
    versions_text = ""
    for pr_num, content in pr_versions.items():
        title = pr_info[pr_num]["title"]
        body = pr_info[pr_num].get("body", "") or ""
        desc = f" — {body[:120]}" if body.strip() else ""
        label = f'PR #{pr_num}: "{title}"{desc}'
        versions_text += f"\n\n=== {label} ===\n{content[:4000]}"

    base_section = f"=== BASE (current main branch) ===\n{base[:4000]}" if base else "=== BASE ===\n(new file — does not exist on main branch yet)"

    prompt = f"""You are a senior software engineer performing an intelligent code merge.

File: {filename}

{base_section}
{versions_text}

Your job:
1. Study all versions carefully.
2. Produce ONE final merged file that intelligently combines the best parts of every PR version with the base.
3. Resolve ALL conflicts — choose the best code, never leave conflict markers.
4. The merged file must be complete (every line), correct, and production-ready.
5. After the code, explain EVERY merge decision clearly.

Respond in EXACTLY this format (no deviations):

### MERGED CODE
```{lang}
<complete merged file here — every single line>
```

### MERGE EXPLANATION
**What was kept from base:**
- bullet

**What was merged from each PR:**
- PR #<n> ("<title>"): bullet explaining what was taken and why

**Conflicts resolved:**
- bullet describing each conflict and the decision made (write "None" if no conflicts)

**Final result:**
One sentence summary of what the merged file achieves."""

    ai_text = call_ai(prompt, max_tokens=1800)

    if not ai_text:
        # Fallback: return the latest PR version as merged
        latest_pr = list(pr_versions.keys())[-1]
        fallback_code = pr_versions[latest_pr]
        title = pr_info[latest_pr]["title"]
        return {
            "merged_code": fallback_code,
            "explanation": f"⚠️ AI unavailable — showing version from PR #{latest_pr} (\"{title}\") as fallback."
        }

    # Parse the AI response into code + explanation
    merged_code = ""
    explanation = ""

    try:
        # Extract code block between first ``` pair after "### MERGED CODE"
        import re
        code_match = re.search(r"### MERGED CODE\s*```[^\n]*\n([\s\S]*?)```", ai_text)
        if code_match:
            merged_code = code_match.group(1).strip()

        # Everything after "### MERGE EXPLANATION"
        exp_match = re.search(r"### MERGE EXPLANATION([\s\S]*)", ai_text)
        if exp_match:
            explanation = exp_match.group(1).strip()

        if not merged_code:
            # Fallback: if parsing failed, use latest PR version
            merged_code = list(pr_versions.values())[-1]
            explanation = ai_text  # Still show full AI text

    except Exception as e:
        print("  Parse error:", e)
        merged_code = list(pr_versions.values())[-1]
        explanation = ai_text

    return {"merged_code": merged_code, "explanation": explanation}


@app.post("/smart-merge")
def smart_merge(data: dict):
    owner = data.get("owner")
    repo = data.get("repo")
    prs = data.get("prs", [])

    if not owner or not repo:
        return {"result": "❌ Missing owner or repo"}
    if not prs or len(prs) < 2:
        return {"result": "❌ Select at least 2 PRs to merge"}
    if not ACCESS_TOKEN:
        return {"result": "❌ Not authenticated — please login with GitHub first"}

    try:
        print(f"🚀 SMART MERGE (AI-FIRST) | PRs: {prs} | Repo: {owner}/{repo}")

        # ─────────────────────────────────────────────────
        # STEP 1: Fetch PR metadata (title, body, head SHA)
        # ─────────────────────────────────────────────────
        pr_info: dict[int, dict] = {}
        for pr_num in prs:
            res = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
            )
            if res.status_code == 200:
                d = res.json()
                pr_info[pr_num] = {
                    "title": d.get("title", f"PR #{pr_num}"),
                    "body":  d.get("body", "") or "",
                    "head_sha": d["head"]["sha"],
                    "head_ref": d["head"]["ref"],
                }
            else:
                pr_info[pr_num] = {
                    "title": f"PR #{pr_num}", "body": "",
                    "head_sha": "HEAD", "head_ref": "HEAD"
                }

        # ─────────────────────────────────────────────────
        # STEP 2: Collect changed filenames across all PRs
        # ─────────────────────────────────────────────────
        # file → list of {pr, status}
        file_pr_map: dict[str, list[dict]] = {}

        for pr_num in prs:
            files_res = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}/files",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
            )
            if files_res.status_code != 200:
                print(f"  ⚠️  Could not fetch files for PR #{pr_num}")
                continue

            for f in files_res.json():
                fname = f.get("filename")
                if not fname:
                    continue
                file_pr_map.setdefault(fname, []).append({
                    "pr": pr_num,
                    "status": f.get("status", "modified")
                })

        if not file_pr_map:
            return {"result": "⚠️ No changed files found across the selected PRs."}

        print(f"  📂 Files to merge: {list(file_pr_map.keys())}")

        # ─────────────────────────────────────────────────
        # STEP 3: For each file — fetch base + each PR ver
        #         then ask AI to produce the merged result
        # ─────────────────────────────────────────────────
        results = []

        for filename, pr_list in file_pr_map.items():
            print(f"\n  🔀 Merging: {filename}")

            # Only process files touched by 2+ PRs OR all selected PRs (for completeness)
            # Fetch base version from main/master
            base_content = _get_file_at_ref(owner, repo, filename, "HEAD")

            # Fetch each PR's version from its head branch
            pr_versions: dict[int, str] = {}
            for item in pr_list:
                pr_num = item["pr"]
                head_sha = pr_info[pr_num]["head_sha"]
                content = _get_file_at_ref(owner, repo, filename, head_sha)
                if content:
                    pr_versions[pr_num] = content
                    print(f"    ✅ Fetched PR #{pr_num} version ({len(content)} chars)")
                else:
                    print(f"    ⚠️  Could not fetch PR #{pr_num} version of {filename}")

            if not pr_versions:
                print(f"    ❌ Skipping {filename} — no PR versions available")
                continue

            # If only one PR has this file, still do AI analysis
            print(f"    🤖 Calling AI merge for {filename}...")
            merge_result = _ai_merge_file(filename, base_content, pr_versions, pr_info)

            results.append({
                "filename": filename,
                "prs": [item["pr"] for item in pr_list],
                "merged_code": merge_result["merged_code"],
                "explanation": merge_result["explanation"],
            })

        if not results:
            return {"result": "❌ Could not fetch file content from GitHub. Check repository access permissions."}

        # ─────────────────────────────────────────────────
        # STEP 4: Build the final output
        # ─────────────────────────────────────────────────
        pr_header = "\n".join(
            f"- **PR #{n}**: {info['title']}" for n, info in pr_info.items()
        )

        output_sections = []
        for r in results:
            lang = _ext(r["filename"])
            pr_tags = ", ".join(f"#{p}" for p in r["prs"])
            section = (
                f"### 📄 File: `{r['filename']}` (from PR {pr_tags})\n\n"
                f"### Final Merged Code\n"
                f"```{lang}\n{r['merged_code']}\n```\n\n"
                f"### Merge Explanation\n{r['explanation']}"
            )
            output_sections.append(section)

        final = (
            f"### Merged PRs\n{pr_header}\n\n"
            + "\n\n---\n\n".join(output_sections)
            + "\n\n### Developer Notes\n"
            "- Full file versions fetched from GitHub (base + each PR head branch)\n"
            "- AI (LLaMA-3-8B) performed intelligent 3-way merge\n"
            "- Copy-paste the merged code directly into your codebase\n"
            "- Simulation only — GitHub push not yet enabled\n"
        )

        print(f"\n✅ SMART MERGE COMPLETE — {len(results)} file(s) merged")

        # Build structured files dict for real PR creation
        files_dict = {r["filename"]: r["merged_code"] for r in results}

        return {
            "result": final,
            "files":  files_dict    # {filename: merged_code} → sent to /apply-merge
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"result": f"❌ Smart merge failed: {str(e)}"}


def _fetch_full_file(owner, repo, filename):
    """Fetch the base file content from GitHub as a list of lines."""
    try:
        res = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{filename}",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )
        if res.status_code == 200:
            content = res.json().get("content", "")
            return base64.b64decode(content).decode("utf-8", errors="replace").splitlines()
    except Exception as e:
        print(f"Fetch file failed ({filename}):", e)
    return []


def _apply_patch(base_lines, filename, patch_text):
    """
    Apply a unified diff patch to base_lines.
    Returns (merged_lines, conflicts_list).
    Conflicts are returned as conflict-marker strings.
    """
    try:
        full_patch = f"--- a/{filename}\n+++ b/{filename}\n{patch_text}"
        patch = PatchSet(full_patch)
    except Exception as e:
        print(f"Patch parse error ({filename}):", e)
        return base_lines, []

    result = base_lines[:]
    conflicts = []
    offset = 0

    for patched_file in patch:
        for hunk in patched_file:
            idx = max(0, hunk.source_start - 1 + offset)

            added_lines = []
            removed_lines = []
            context_lines = []

            for line in hunk:
                val = line.value.rstrip("\n")
                if line.is_context:
                    added_lines.append(val)
                    removed_lines.append(val)
                    context_lines.append(val)
                elif line.is_added:
                    added_lines.append(val)
                elif line.is_removed:
                    removed_lines.append(val)

            end = idx + len(removed_lines)
            existing = result[idx:end]

            if existing == removed_lines:
                # Clean apply
                result[idx:end] = added_lines
                offset += len(added_lines) - len(removed_lines)
            else:
                # Conflict detected
                conflict_block = [
                    "<<<<<<< CURRENT",
                    *existing,
                    "=======",
                    *added_lines,
                    ">>>>>>> INCOMING"
                ]
                result[idx:end] = conflict_block
                offset += len(conflict_block) - len(existing)
                conflicts.append("\n".join(conflict_block))

    return result, conflicts


def _resolve_conflict_with_ai(conflict_text: str) -> str:
    """Ask AI to resolve a single merge conflict block. Returns resolved code or empty string."""
    prompt = f"""You are an expert software engineer. Resolve the Git merge conflict below.
Return ONLY the final resolved code — no explanations, no conflict markers.

{conflict_text}"""
    return call_ai(prompt, max_tokens=300)


@app.post("/smart-merge")
def smart_merge(data: dict):
    owner = data.get("owner")
    repo = data.get("repo")
    prs = data.get("prs", [])

    if not owner or not repo:
        return {"result": "❌ Missing owner or repo"}
    if not prs or len(prs) < 2:
        return {"result": "❌ Select at least 2 PRs to merge"}
    if not ACCESS_TOKEN:
        return {"result": "❌ Not authenticated — please login with GitHub first"}

    try:
        print(f"🚀 SMART MERGE STARTED for PRs: {prs} | Repo: {owner}/{repo}")

        # ─────────────────────────────────────────
        # STEP 1: Collect all patches from each PR
        # ─────────────────────────────────────────
        file_patches: dict[str, list[dict]] = {}
        pr_titles: dict[int, str] = {}

        for pr_num in prs:
            # Get PR meta for title
            pr_meta = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
            )
            if pr_meta.status_code == 200:
                pr_titles[pr_num] = pr_meta.json().get("title", f"PR #{pr_num}")
            else:
                pr_titles[pr_num] = f"PR #{pr_num}"

            # Get changed files
            files_res = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}/files",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
            )
            if files_res.status_code != 200:
                print(f"⚠️  Could not fetch files for PR #{pr_num}: {files_res.status_code}")
                continue

            for f in files_res.json():
                filename = f.get("filename")
                patch = f.get("patch")
                status = f.get("status", "modified")

                if not filename or not patch:
                    continue

                file_patches.setdefault(filename, []).append({
                    "pr": pr_num,
                    "patch": patch,
                    "status": status
                })

        if not file_patches:
            return {"result": "⚠️ No patchable files found across selected PRs. They may have no code changes or contain only binary files."}

        # ─────────────────────────────────────────
        # STEP 2: Apply patches file by file
        # ─────────────────────────────────────────
        merged_files: dict[str, str] = {}
        all_conflicts: list[dict] = []
        pr_file_map: dict[int, list[str]] = {pr: [] for pr in prs}

        for filename, patches in file_patches.items():
            for p in patches:
                pr_file_map[p["pr"]].append(filename)

            base_lines = _fetch_full_file(owner, repo, filename)
            if not base_lines:
                print(f"⚠️  Skipping {filename} — could not fetch base content")
                continue

            current = base_lines
            file_conflict_list = []

            for p in patches:
                current, conflicts = _apply_patch(current, filename, p["patch"])
                if conflicts:
                    file_conflict_list.extend([{"pr": p["pr"], "text": c} for c in conflicts])

            merged_files[filename] = "\n".join(current)

            if file_conflict_list:
                all_conflicts.append({"file": filename, "conflicts": file_conflict_list})

        if not merged_files:
            return {"result": "❌ Could not fetch base content for any changed file. Check repo access."}

        print(f"✅ Patch application done. Files merged: {len(merged_files)}, Conflict files: {len(all_conflicts)}")

        # ─────────────────────────────────────────
        # STEP 3: AI conflict resolution
        # ─────────────────────────────────────────
        resolved_conflicts: list[dict] = []

        for conflict_item in all_conflicts:
            filename = conflict_item["file"]
            for c in conflict_item["conflicts"]:
                pr_num = c["pr"]
                conflict_text = c["text"]
                print(f"🤖 Resolving conflict in {filename} (PR #{pr_num})...")

                resolved = _resolve_conflict_with_ai(conflict_text)

                if not resolved:
                    # Rule-based fallback: prefer incoming (latest PR wins)
                    lines = conflict_text.splitlines()
                    try:
                        sep = lines.index("=======")
                        end = lines.index(">>>>>>> INCOMING")
                        resolved = "\n".join(lines[sep + 1:end])
                    except ValueError:
                        resolved = conflict_text  # keep as-is

                resolved_conflicts.append({
                    "file": filename,
                    "pr": pr_num,
                    "original": conflict_text,
                    "resolved": resolved
                })

        # ─────────────────────────────────────────
        # STEP 4: Build clean output
        # ─────────────────────────────────────────
        pr_summary_lines = [f"- **PR #{n}**: {t}" for n, t in pr_titles.items()]
        pr_summary = "\n".join(pr_summary_lines)

        files_changed_lines = []
        for filename, patches in file_patches.items():
            prs_touching = list({p["pr"] for p in patches})
            files_changed_lines.append(f"- `{filename}` (touched by PR#{', #'.join(map(str, prs_touching))})")
        files_summary = "\n".join(files_changed_lines)

        merged_code_sections = []
        for filename, code in merged_files.items():
            lang = filename.rsplit(".", 1)[-1] if "." in filename else ""
            merged_code_sections.append(f"**`{filename}`**\n```{lang}\n{code}\n```")
        merged_code_block = "\n\n".join(merged_code_sections)

        if resolved_conflicts:
            conflict_section_lines = []
            for rc in resolved_conflicts:
                conflict_section_lines.append(
                    f"**`{rc['file']}`** (conflict from PR #{rc['pr']})\n"
                    f"```\n{rc['resolved']}\n```"
                )
            conflict_section = "\n\n".join(conflict_section_lines)
        else:
            conflict_section = "✅ No conflicts detected — all patches applied cleanly."

        final = f"""### Merged PRs
{pr_summary}

### Files Changed
{files_summary}

### Final Merged Code
{merged_code_block}

### Conflict Resolution
{conflict_section}

### Developer Notes
- Base file fetched from GitHub main branch
- Patches applied sequentially (oldest PR first)
- Conflicts resolved via HuggingFace AI (Mistral-7B) with rule-based fallback
- Simulation only — push to GitHub not yet enabled
"""

        return {"result": final}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"result": f"❌ Smart merge failed: {str(e)}"}


    
# -----------------------------
# 🟢 MERGE READY AI
# -----------------------------
@app.post("/merge-ready")
def merge_ready(data: dict):
    owner = data.get("owner")
    repo = data.get("repo")

    if not ACCESS_TOKEN:
        return {"result": "❌ Not authenticated"}

    try:
        print("🚀 Fetching PRs for merge-ready...")

        res = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
        )

        if res.status_code != 200:
            return {"result": "❌ Failed to fetch PRs"}

        prs = res.json()
        if not prs:
            return {"result": "No open PRs found"}

        ready, risky, conflict = [], [], []
        summary_for_ai = ""

        for pr in prs[:6]:
            detail = requests.get(
                pr["url"],
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
            ).json()

            state = detail.get("mergeable_state", "unknown")
            summary_for_ai += f"PR #{pr['number']}: {pr['title']} — state: {state}\n"

            if state == "clean":
                ready.append(pr["number"])
            elif state in ["dirty", "conflicting"]:
                conflict.append(pr["number"])
            else:
                risky.append(pr["number"])

        print(f"📊 Ready: {ready} | Risky: {risky} | Conflict: {conflict}")

        prompt = f"""You are a senior software engineer analyzing GitHub PRs for merge readiness.
Based on the data below, respond EXACTLY in this format:

### Ready to Merge
- PR numbers that are clean

### Risky PRs
- PR numbers that need review

### Conflicts
- PR numbers with merge conflicts

### Final Recommendation
- Concrete action steps for the developer

PR Data:
{summary_for_ai}"""

        ai_output = call_ai(prompt, max_tokens=300)

        if not ai_output:
            print("⚠️ AI unavailable — using structured fallback")
            ai_output = (
                f"### Ready to Merge\n"
                + ("\n".join(f"- PR #{p}" for p in ready) or "- None") +
                f"\n\n### Risky PRs\n"
                + ("\n".join(f"- PR #{p}" for p in risky) or "- None") +
                f"\n\n### Conflicts\n"
                + ("\n".join(f"- PR #{p}" for p in conflict) or "- None") +
                "\n\n### Final Recommendation\n"
                "- Merge READY PRs first\n"
                "- Review RISKY PRs before merging\n"
                "- Fix conflicts before attempting merge"
            )

        return {
            "ready": ready,
            "risky": risky,
            "conflict": conflict,
            "ai": ai_output
        }

    except Exception as e:
        print("🔥 MERGE READY ERROR:", str(e))
        return {"result": "❌ MergeReady failed"}