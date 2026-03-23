# Claude Code Setup Guide

Everything you need to go from zero to a solid Claude Code environment.

---

## 1. Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

Then authenticate:

```bash
claude
# Follow the login prompt — opens browser to claude.ai
```

Verify it works:

```bash
claude --version
```

---

## 2. How Claude Code works

- Run `claude` inside any project directory to start a session
- Claude reads your codebase, runs commands, edits files, and uses git on your behalf
- It will ask for permission before doing anything risky (pushing, deleting, etc.) unless you configure it otherwise

---

## 3. Global settings (`~/.claude/settings.json`)

This file controls Claude's behavior across all projects. Create it if it doesn't exist:

```bash
mkdir -p ~/.claude
```

Minimal useful config:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": ["Skill"]
  }
}
```

You can add more permissions to auto-approve tools you trust, e.g.:

```json
"allow": ["Skill", "Bash(npm run *)", "Bash(git status)", "Bash(git log *)"]
```

---

## 4. Global CLAUDE.md (`~/.claude/CLAUDE.md`)

This is your personal instruction file — Claude reads it at the start of every session regardless of which project you're in. Great for personal preferences.

```bash
touch ~/.claude/CLAUDE.md
```

Example contents:

```markdown
# My Claude Preferences

- Prefer concise responses. No filler words or preamble.
- Always run linting/tests before considering a task done.
- When writing Python, follow PEP 8 and use type hints.
- Prefer editing existing files over creating new ones.
- Never commit without being explicitly asked.
- Ask before pushing to remote.
```

Add whatever matters to you. This travels with you across all projects.

---

## 5. Project CLAUDE.md

Each project can also have its own `CLAUDE.md` in the root directory. Claude merges it with your global one. Use it for:

- How to build and run the project
- Architecture overview
- Key files and what they do
- Project-specific rules (e.g. "never modify the generated/ folder")

The more context you give Claude about the project here, the better it performs.

---

## 6. Hooks

Hooks are shell scripts that run automatically on Claude Code events. Configure them in `~/.claude/settings.json`.

### Stop hook — enforce git hygiene

Blocks Claude from finishing a session if there are uncommitted or unpushed changes. Useful when working in managed environments.

Create `~/.claude/stop-hook-git-check.sh`:

```bash
#!/bin/bash
input=$(cat)

# Prevent recursion
if [[ "$(echo "$input" | jq -r '.stop_hook_active')" == "true" ]]; then exit 0; fi

# Skip if not a git repo
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Uncommitted changes present. Please commit and push before finishing." >&2
  exit 2
fi

# Check for untracked files
if [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
  echo "Untracked files present. Please commit and push before finishing." >&2
  exit 2
fi

# Check for unpushed commits
current_branch=$(git branch --show-current)
if git rev-parse "origin/$current_branch" >/dev/null 2>&1; then
  unpushed=$(git rev-list "origin/$current_branch..HEAD" --count 2>/dev/null) || unpushed=0
  if [[ "$unpushed" -gt 0 ]]; then
    echo "$unpushed unpushed commit(s) on '$current_branch'. Please push." >&2
    exit 2
  fi
fi

exit 0
```

```bash
chmod +x ~/.claude/stop-hook-git-check.sh
```

Then register it in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/stop-hook-git-check.sh"
          }
        ]
      }
    ]
  }
}
```

Other hook events: `PreToolUse`, `PostToolUse`, `Notification`, `SessionStart`

---

## 7. MCP servers (optional but powerful)

MCP (Model Context Protocol) servers give Claude access to external tools and data sources directly in the session.

### GitHub MCP — most useful for developers

Lets Claude read issues, PRs, comments, and repo metadata directly without copy-pasting.

Install the GitHub MCP server:

```bash
claude mcp add github -- npx -y @modelcontextprotocol/server-github
```

You'll need a GitHub personal access token with `repo` scope. Set it:

```bash
export GITHUB_TOKEN=ghp_yourtoken
# Or add it to your shell profile (~/.bashrc / ~/.zshrc)
```

Now Claude can do things like "summarize the open issues" or "check what's failing on this PR" without leaving the terminal.

### Other useful MCP servers

```bash
# Filesystem access (more explicit file operations)
claude mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem /path/to/allow

# Fetch web pages
claude mcp add fetch -- npx -y @modelcontextprotocol/server-fetch

# PostgreSQL
claude mcp add postgres -- npx -y @modelcontextprotocol/server-postgres postgresql://localhost/mydb
```

List what you have installed:

```bash
claude mcp list
```

---

## 8. Useful CLI flags

```bash
claude                        # Start interactive session
claude -p "fix the login bug" # One-shot prompt (non-interactive)
claude --continue             # Resume the last session
claude --model claude-opus-4-6  # Use a specific model
claude /help                  # List slash commands inside a session
```

Inside a session, useful slash commands:

| Command | What it does |
|---------|-------------|
| `/clear` | Clear conversation history |
| `/compact` | Summarize history to save context |
| `/cost` | Show token usage for the session |
| `/diff` | Show all file changes made this session |
| `/status` | Show current model and config |

---

## 9. Quick checklist

- [ ] `npm install -g @anthropic-ai/claude-code`
- [ ] Run `claude` and log in
- [ ] Create `~/.claude/settings.json` with base permissions
- [ ] Create `~/.claude/CLAUDE.md` with your personal preferences
- [ ] Add a Stop hook for git hygiene (if working in a managed/team environment)
- [ ] Add GitHub MCP if you work with GitHub repos
- [ ] Add a `CLAUDE.md` to each project you use Claude on

---

## Tips

- **Context is everything.** The better your `CLAUDE.md` files, the better Claude performs. Describe the architecture, key files, and what not to touch.
- **Keep sessions focused.** Use `/clear` or start a new session when switching tasks — context from unrelated work can confuse Claude.
- **Review before you approve.** Claude will show you what it plans to do for risky actions. Read it.
- **`claude -p` for scripts.** You can pipe Claude into shell scripts for automated tasks — useful for CI or batch operations.
