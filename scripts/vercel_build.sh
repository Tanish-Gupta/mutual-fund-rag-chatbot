#!/usr/bin/env bash
# Runs on Vercel after install: static UI into public/, optional index bundle into data/index/.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p public
cp -f "$ROOT/phase4/web/"* "$ROOT/public/"
# Serve chat at site root (/)
cp -f "$ROOT/phase4/web/chat.html" "$ROOT/public/index.html"

mkdir -p data/index
if [[ -d "$ROOT/vercel-bundle/index" ]] && compgen -G "$ROOT/vercel-bundle/index/*" > /dev/null; then
  cp -R "$ROOT/vercel-bundle/index/"* "$ROOT/data/index/"
fi

echo "vercel_build: public/ ready; data/index/ run dirs: $(ls -1 data/index 2>/dev/null | wc -l | tr -d ' ')"
