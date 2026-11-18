#!/bin/bash
# Runs a command on the Node major version pinned in frontend/.nvmrc.
# Git hooks and other non-interactive shells often resolve an older system Node
# ahead of nvm, so `make check` cannot trust whatever `node` is first on PATH.
# If the right Node is already active it is used as is (CI); otherwise nvm is
# tried; otherwise this fails loudly rather than run the checks on the wrong Node.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
want="$(tr -d '[:space:]v' < "$root/frontend/.nvmrc")"
want_major="${want%%.*}"

node_major() {
  command -v node >/dev/null 2>&1 || { echo none; return; }
  node -p 'process.versions.node.split(".")[0]'
}

if [ "$(node_major)" != "$want_major" ]; then
  nvm_sh="${NVM_DIR:-$HOME/.nvm}/nvm.sh"
  if [ -s "$nvm_sh" ]; then
    set +eu
    # shellcheck disable=SC1090
    . "$nvm_sh" >/dev/null 2>&1
    nvm use "$want" >/dev/null 2>&1
    set -eu
  fi
fi

have="$(node_major)"
if [ "$have" != "$want_major" ]; then
  echo "with-node: need Node $want_major (frontend/.nvmrc) but found: $have." >&2
  echo "with-node: install it, for example: nvm install $want_major" >&2
  exit 1
fi

exec "$@"
