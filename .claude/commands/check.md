---
allowed-tools: Read, Glob, Grep, Bash(ruff:*), Bash(ruff check:*), Bash(ruff format:*), Bash(pytest:*), Bash(python3.12 -m pytest:*), Bash(npm run lint:*), Bash(npm run build:*), Bash(git diff:*)
description: Full pre-commit check — lint, format, and tests across backend and frontend
---

Run the full quality check suite before committing. Show current diff first:

```
git diff --stat HEAD
```

Then run in order:

1. **Backend lint**: `cd backend && ruff check . && ruff format --check .`
2. **Backend tests**: `cd backend && source venv/bin/activate && python3.12 -m pytest tests/ -v --tb=short -q`
3. **Frontend lint**: `cd frontend && npm run lint`

Stop at the first failure and report it clearly. If everything passes, confirm it's ready to commit.
