---
allowed-tools: Read, Glob, Grep, Bash(pytest:*), Bash(python3.12 -m pytest:*)
description: Run the backend test suite and report failures with analysis
---

Run the backend tests from the `backend/` directory:

```
cd backend && source venv/bin/activate && python3.12 -m pytest tests/ -v --tb=short 2>&1
```

If any tests fail:
1. Show the failure output grouped by test file
2. Read the relevant source files to understand the failure
3. Identify whether it's a test issue or a code bug
4. Suggest a concrete fix

If all tests pass, report the count and any warnings worth noting.
