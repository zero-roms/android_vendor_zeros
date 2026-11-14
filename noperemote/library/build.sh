#!/bin/bash
#
# Build ZeroS's remote library (noperemote-library.zip, next to this script)
# from the inputs fetch-sources.sh put in <dir>. The same inputs give the same
# zip; report.txt records the counts and its checksum.
#
#   build.sh <dir>
#
# SPDX-License-Identifier: Apache-2.0
#
set -euo pipefail
DIR=${1:?usage: build.sh <dir>}
HERE=$(cd "$(dirname "$0")" && pwd)
LIB="$DIR/flipperzero-firmware/lib/infrared/encoder_decoder"

cc -O2 -std=gnu11 -w -I"$HERE/irtool" -I"$LIB" -o "$DIR/irtool" \
    "$HERE/irtool/irtool.c" $(find "$LIB" -name '*.c' | sort)
python3 -I "$HERE/build-library.py" "$DIR/IRDB" "$DIR/Flipper-IRDB" \
    "$DIR/irext/irext_db_20260929_sqlite3.db" "$DIR/irtool" "$DIR/out"
cp "$DIR/out/noperemote-library.zip" "$DIR/out/report.txt" "$HERE/"
