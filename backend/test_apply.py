"""
Quick test: hit /apply-merge directly to confirm the endpoint works.
Run: python test_apply.py
"""
import requests

res = requests.post(
    "http://localhost:8000/apply-merge",
    json={
        "owner": "test",
        "repo":  "test",
        "prs":   [1, 2],
        "merged_files": {}          # empty — should return the "no files" error cleanly
    },
    timeout=10
)
print("Status:", res.status_code)
print("Body:  ", res.json())
