#!/bin/bash
# PostToolUse hook for Edit|Write: formats the edited file so diffs stay clean.
# It knows no language. If the project's Makefile has a `format` target, it runs
# `make format FILE=<path>`; otherwise it does nothing. Lint fixes are left to `make check`.
# Never blocks. A failing formatter exits 1, which shows the message without stopping the edit.
INPUT=$(cat)
FILE_PATH=$(printf '%s' "$INPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)
[ -n "$FILE_PATH" ] && [ -f "$FILE_PATH" ] || exit 0
cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0
[ -f Makefile ] && grep -q '^format:' Makefile || exit 0

if ! make -s format FILE="$FILE_PATH" >/dev/null 2>&1; then
  echo "format hook: 'make format FILE=$FILE_PATH' failed. The file was left as written." >&2
  exit 1
fi
exit 0
