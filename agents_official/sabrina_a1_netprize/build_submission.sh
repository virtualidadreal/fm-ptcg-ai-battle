#!/usr/bin/env bash
# Pack Sabrina A1 net-prize-trade (Alakazam fork of v3) into submission.tar.gz = main.py +
# deck.csv + cg/ (the local engine shipped in this dir). Location-independent.
# Usage:  bash build_submission.sh   (builds the tar; does NOT submit)
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
cp "$SRC/main.py"  "$TMP/main.py"
cp "$SRC/deck.csv" "$TMP/deck.csv"
if [ -d "$SRC/cg" ]; then
  cp -r "$SRC/cg" "$TMP/cg"
else
  echo "ERROR: $SRC/cg missing (need the engine package for cabt + the Kaggle runtime)" >&2
  exit 1
fi
# sanity: deck must be 60 ids, agent must be the LAST callable (get_last_callable gotcha)
n=$(grep -c . "$SRC/deck.csv"); [ "$n" -eq 60 ] || { echo "ERROR: deck.csv has $n ids, need 60" >&2; exit 1; }
( cd "$TMP" && tar -czf "$SRC/submission.tar.gz" --exclude='__pycache__' . )
echo "Done: $SRC/submission.tar.gz"
tar -tzf "$SRC/submission.tar.gz" | grep -E "main.py|deck.csv|cg/api" || true
