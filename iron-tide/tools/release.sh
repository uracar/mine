#!/usr/bin/env bash
# Bump the version everywhere, build the single-file game and copy it to dist/iron-tide-vX.Y.html, then refresh the code map.
# Usage (from iron-tide/):  tools/release.sh 7.0      (no Netlify: the owner gets the versioned HTML file)
set -euo pipefail
cd "$(dirname "$0")/.."
V="$1"
sed -i -E "s/GAME_VERSION='v[0-9.]+'/GAME_VERSION='v$V'/" js/game.js
sed -i -E "s/const VERSION='iron-tide-[0-9.]+'/const VERSION='iron-tide-$V.0'/" sw.js
node -e "new Function(require('fs').readFileSync('js/game.js','utf8'))"   # syntax check
python3 tools/bundle.py
cp dist/iron-tide.html "dist/iron-tide-v$V.html"
python3 tools/codemap.py
echo "built dist/iron-tide-v$V.html - now: node tools/test/it.js nodes file://$PWD/dist/iron-tide-v$V.html#play&q=1&still"
