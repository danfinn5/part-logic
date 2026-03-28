---
allowed-tools: Read, Glob, Grep, Bash(ruff:*), Bash(ruff check:*), Bash(ruff format:*), Bash(npm run lint:*)
description: Run ruff on the backend and ESLint on the frontend, report all issues
---

Run linting for both backend and frontend:

**Backend** (from repo root):
```
cd backend && ruff check . && ruff format --check .
```

**Frontend** (from repo root):
```
cd frontend && npm run lint
```

Report all issues found. If `--fix` can resolve them automatically, say so. Group issues by file.
