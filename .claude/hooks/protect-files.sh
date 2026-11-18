#!/bin/bash
# PreToolUse hook for Edit|Write: blocks secrets, lockfiles, git internals and generated files,
# and asks the human before the harness's own guard files are changed.
# Exit 2 blocks the edit and sends the stderr message back to Claude as feedback.
# Project-specific generated files go in .claude/hooks/protected-paths.txt, one glob per line.
# Needs python3. If the input cannot be read, the edit is blocked rather than waved through.
INPUT=$(cat)
FILE_PATH=$(printf '%s' "$INPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)
if [ -z "$FILE_PATH" ]; then
  echo "Blocked: protect-files.sh could not read file_path from the hook input (is python3 installed?). Blocking to be safe." >&2
  exit 2
fi

case "$FILE_PATH" in
  .env.example|*/.env.example|.env.*.example|*/.env.*.example)
    ;;
  .env|*/.env|.env.*|*/.env.*)
    echo "Blocked: $FILE_PATH holds secrets. Never touch .env; document new variables in .env.example." >&2
    exit 2
    ;;
  .git|*/.git|.git/*|*/.git/*)
    echo "Blocked: $FILE_PATH is git internals. Use git commands instead." >&2
    exit 2
    ;;
  *.lock|*.lockb|*-lock.json|*-lock.yaml|go.sum|*/go.sum|Package.resolved|*/Package.resolved|gradle.lockfile|*/gradle.lockfile)
    echo "Blocked: $FILE_PATH is a lockfile. Change dependencies through the package manager." >&2
    exit 2
    ;;
esac

LIST="$CLAUDE_PROJECT_DIR/.claude/hooks/protected-paths.txt"
if [ -f "$LIST" ]; then
  while IFS= read -r pattern || [ -n "$pattern" ]; do
    # Trim surrounding whitespace (and a Windows line ending), or the glob silently never matches.
    pattern="${pattern#"${pattern%%[![:space:]]*}"}"
    pattern="${pattern%"${pattern##*[![:space:]]}"}"
    case "$pattern" in ''|'#'*) continue ;; esac
    # shellcheck disable=SC2254
    case "$FILE_PATH" in
      $pattern|*/$pattern)
        echo "Blocked: $FILE_PATH is generated or protected in this project. Change its source and regenerate." >&2
        exit 2
        ;;
    esac
  done < "$LIST"
fi

# The guard files themselves: not blocked (Phase 0 has to adapt them), but the human is asked each time.
case "$FILE_PATH" in
  .claude/settings.json|*/.claude/settings.json|.claude/settings.local.json|*/.claude/settings.local.json|.claude/hooks/*|*/.claude/hooks/*|.githooks/*|*/.githooks/*|.github/workflows/*|*/.github/workflows/*)
    printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"This file is part of the guardrails (settings, hooks, pre-commit or CI). Confirm the change does not weaken a check."}}'
    exit 0
    ;;
esac
exit 0
