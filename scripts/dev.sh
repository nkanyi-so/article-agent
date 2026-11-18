#!/bin/bash
# Runs the backend (demo mode, :8000) and the frontend (:3000) together and stops
# both when either exits or this script is interrupted or terminated.
# Demo mode is forced: the live client is never started from here.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pids=()

stop_all() {
  trap - INT TERM EXIT
  for pid in "${pids[@]}"; do
    # Each server is its own process group (set -m below), so its reloader and
    # worker children go with it.
    kill -TERM -- "-$pid" 2>/dev/null
  done
  wait 2>/dev/null
}
trap stop_all INT TERM EXIT

set -m
(cd "$root/backend" && APP_MODE=demo exec uv run --locked uvicorn app.main:create_app --factory --reload --port 8000) &
pids+=("$!")
(cd "$root/frontend" && exec "$root/scripts/with-node.sh" npm run dev) &
pids+=("$!")
set +m

# Return as soon as either server stops, so a crash in one does not leave the other
# running. A polling loop because macOS ships bash 3.2, which has no `wait -n`.
while kill -0 "${pids[0]}" 2>/dev/null && kill -0 "${pids[1]}" 2>/dev/null; do
  sleep 1
done
