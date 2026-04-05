import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the broken print line with a clean one
fixed = re.sub(
    r'    print\("[^"]*APPLY MERGE CALLED[^"]*", prs, "[^"]*", list\(merged_files\.keys\(\)\)\)',
    '    print("APPLY MERGE CALLED | PRs:", prs, "| Files:", list(merged_files.keys()))',
    content
)

if fixed != content:
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(fixed)
    print("SUCCESS - line fixed")
else:
    print("Pattern not found - printing line 307:")
    lines = content.splitlines()
    print(repr(lines[306]))
