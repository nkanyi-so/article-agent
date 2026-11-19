#!/usr/bin/env bash
# Takes every main state of the screen, in light and dark, at desktop and phone width,
# into docs/screens/. Needs the backend in demo mode on :8000, the frontend on :3000
# (a production build gives clean shots: `npm run build && npm run start`), and Chrome.
#
#   scripts/screenshots.sh
#
# The phone shots are taken through a 390px frame, because headless Chrome will not make
# a window narrower than 500px.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$root/docs/screens"
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
base="http://localhost:3000"
run="seed-sallowfield-dental"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$out"

# The first sentence after the lead that has a question added by code.
with_question="$(curl -s "localhost:8000/api/runs/$run" | python3 -c "
import json, sys
claims = json.load(sys.stdin)['article']['claims']
print(next(i for i, c in enumerate(claims) if c['question_segments'] and i > 0))")"

capture() { # file url width height wait
  # A settled page is given virtual time to finish loading. A page caught mid-run
  # ("live") is given real time instead, because the stages arrive in real time.
  local timing=(--virtual-time-budget=9000)
  [[ "$5" == live ]] && timing=(--timeout=2600)
  # A profile of its own for every shot: a browser stopped mid-run leaves its profile in a
  # state where the next browser's requests never finish.
  local profile
  profile="$(mktemp -d "$work/profile.XXXXXX")"
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --user-data-dir="$profile" --no-first-run \
    --window-size="$3,$4" "${timing[@]}" --screenshot="$1" "$2" >/dev/null 2>&1
}

shot() { # name path [settled|live] [tall]
  # "tall" makes the window long enough to show the whole page: the lists and the trace
  # sit below the article.
  local name="$1" path="$2" wait="${3:-settled}" sep="?" high=1100 phone_high=1400
  [[ "${4:-}" == tall ]] && high=3000 && phone_high=5600
  [[ "$path" == *\?* ]] && sep="&"
  for theme in light dark; do
    local url="$base$path${sep}theme=$theme"
    capture "$out/$name-$theme-desktop.png" "$url" 1440 "$high" "$wait"
    local frame="$work/frame.html"
    # The frame sits in the middle of a 500px window and the middle 390px are kept.
    printf '<body style="margin:0;background:#888"><iframe src="%s" style="width:390px;height:%spx;border:0;display:block;margin:0 auto"></iframe>' "$url" "$phone_high" >"$frame"
    capture "$out/$name-$theme-phone.png" "file://$frame" 500 "$phone_high" "$wait"
    sips --cropToHeightWidth "$phone_high" 390 "$out/$name-$theme-phone.png" >/dev/null
  done
}

shot 01-entry "/"
shot 03-run "/runs/$run"
shot 03-run-whole-page "/runs/$run" settled tall
shot 04-sentence-with-question "/runs/$run?claim=$with_question"
shot 05-sentence-flagged "/runs/$run?claim=0"
shot 06-headline-flagged "/runs/$run?claim=headline"
shot 07-trace-stage-open "/runs/$run?stage=ground" settled tall
shot 09-missing-run "/runs/no-such-run"
# The two caught mid-run come last: each leaves an abandoned run in the sidebar.
shot 02-live-stages "/?start=quillmoor-books" live
shot 08-rerun-from-draft "/runs/$run?rerun=draft" live
echo "wrote $(ls "$out" | wc -l | tr -d ' ') files to $out"
