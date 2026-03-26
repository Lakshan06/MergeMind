from main import ai_suggest

data = {"patch": "diff --git a/file b/file\n+ print('hello world')"}
result = ai_suggest(data)
print("RESULT:", result)
