#!/bin/bash
#
# Rebuild the ZeroS boot animation (design B1 "orbit") from make-frames.swift.
# Run on the Mac (needs Swift and macOS Core Text):
#
#   make-bootanimation.sh <Roboto variable TTF>
#
# Roboto is Android's system font (Apache 2.0); the copy used for the shipped
# zip came from ZeroS 0.4.0's /system/fonts/Roboto-Regular.ttf (sha256 in
# SOURCE). Android needs the zip stored without compression.
#
# SPDX-License-Identifier: Apache-2.0
#

set -euo pipefail
FONT=${1:?usage: make-bootanimation.sh <Roboto variable TTF>}
HERE=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
swift "$HERE/make-frames.swift" "$FONT" "$tmp"
(cd "$tmp" && zip -0 -X -q -r "$tmp/out.zip" desc.txt part0 part1)
# The file is named after its own checksum: LineageOS's bootanimation genrule
# copies TARGET_BOOTANIMATION without declaring it as an input, so the build
# only notices a new animation when the path changes (bug B17).
sum=$(shasum -a 256 "$tmp/out.zip" | awk '{print $1}')
name="bootanimation-${sum:0:8}.zip"
rm -f "$HERE"/bootanimation-*.zip
mv "$tmp/out.zip" "$HERE/$name"
echo "$name: $(unzip -l "$HERE/$name" | tail -1 | awk '{print $2}') files, sha256 $sum"
echo "Now set TARGET_BOOTANIMATION := vendor/zeros/bootanimation/$name in config/common.mk"
