#!/bin/bash
#
# Fetch the inputs of ZeroS's remote library at the commits pinned below, for
# build.sh. Each input goes into its own folder under <dir>.
#
#   fetch-sources.sh <dir>
#
# SPDX-License-Identifier: Apache-2.0
#
set -euo pipefail
DIR=${1:?usage: fetch-sources.sh <dir>}
HERE=$(cd "$(dirname "$0")" && pwd)

IRDB_COMMIT=f7b15366521cc81ba11b341538f0097bddbb748b          # flipperdevices/IRDB, MIT
FLIPPER_IRDB_COMMIT=d126fb1b6f1e114c52b4a8c19839ea65e3a9c24d   # Lucaslhm/Flipper-IRDB
IREXT_COMMIT=fb3b471d73e118463cf609e096188f837fa8d684          # irext/database, MIT
IREXT_DB=irext_db_20260929_sqlite3.db
IREXT_SHA256=fc9507bb6a0bd65fb7d407b7a65287e66ccaa00f80067ae9cc7a425cdfaca571
FIRMWARE_COMMIT=a8a24de3ff394f77d599ea8ba9c073398670c880       # flipperdevices/flipperzero-firmware, GPL-3.0

fetch_commit() { # <url> <commit> <dest> [sparse path]
    rm -rf "$3"; git init -q "$3"
    git -C "$3" remote add origin "$1"
    if [ -n "${4:-}" ]; then git -C "$3" sparse-checkout set "$4"; fi
    git -C "$3" fetch -q --depth 1 --filter=blob:none origin "$2"
    git -C "$3" checkout -q FETCH_HEAD
}

mkdir -p "$DIR"
echo "==> Flipper Devices IRDB"
fetch_commit https://github.com/flipperdevices/IRDB.git $IRDB_COMMIT "$DIR/IRDB"

echo "==> Flipper-IRDB (CC0 files only)"
grep -v '^#' "$HERE/flipper-irdb-cc0-files.txt" | while IFS= read -r f; do
    [ -n "$f" ] || continue
    mkdir -p "$DIR/Flipper-IRDB/$(dirname "$f")"
    curl -fsSL --retry 3 -o "$DIR/Flipper-IRDB/$f" \
        "https://raw.githubusercontent.com/Lucaslhm/Flipper-IRDB/$FLIPPER_IRDB_COMMIT/$(python3 -I -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$f")"
done

echo "==> IREXT"
mkdir -p "$DIR/irext"
curl -fsSL --retry 3 -o "$DIR/irext/$IREXT_DB" \
    "https://media.githubusercontent.com/media/irext/database/$IREXT_COMMIT/db/$IREXT_DB"
echo "$IREXT_SHA256  $DIR/irext/$IREXT_DB" | shasum -a 256 -c -

echo "==> Flipper firmware lib/infrared"
fetch_commit https://github.com/flipperdevices/flipperzero-firmware.git $FIRMWARE_COMMIT \
    "$DIR/flipperzero-firmware" lib/infrared/encoder_decoder
