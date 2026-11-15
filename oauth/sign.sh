#!/bin/bash
# Signs the OAuth shortcuts so iPhone and iPad will import them.
# Run on a Mac (macOS 12 or later): bash oauth/sign.sh
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p signed
for f in unsigned/*.shortcut; do
  name="$(basename "$f")"
  echo "Signing $name"
  shortcuts sign --mode anyone --input "$f" --output "signed/$name"
done
echo "Done. Signed files are in $(pwd)/signed"
