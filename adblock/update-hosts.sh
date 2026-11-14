#!/bin/bash
#
# Replace the ZeroS blocklist with StevenBlack's "hosts" at a given commit and
# print what to record in SOURCE. Run on the Mac, from anywhere:
#
#   update-hosts.sh <full commit sha>
#
# SPDX-License-Identifier: Apache-2.0
#

set -euo pipefail
COMMIT=${1:?usage: update-hosts.sh <full commit sha of StevenBlack/hosts>}
HERE=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
base="https://raw.githubusercontent.com/StevenBlack/hosts/$COMMIT"
curl -sS --fail -o "$tmp/hosts" "$base/hosts"
curl -sS --fail -o "$tmp/license" "$base/license.txt"
# Refuse anything that is not a plain hosts file with the localhost entries
grep -q '^127\.0\.0\.1 localhost$' "$tmp/hosts"
grep -q '^::1 localhost$' "$tmp/hosts"
! grep -q -v -E '^([[:space:]]*(#.*)?|(0\.0\.0\.0|127\.0\.0\.1|255\.255\.255\.255|::1|fe80::1%lo0|ff0[0-9]::[0-9a-z]+) [^ ]+([[:space:]]+#.*)?)$' "$tmp/hosts"
mv "$tmp/hosts" "$HERE/hosts"
mv "$tmp/license" "$HERE/LICENSE-StevenBlack-hosts"
echo "commit:   $COMMIT"
echo "size:     $(wc -c < "$HERE/hosts" | tr -d ' ') bytes, $(grep -c '^0\.0\.0\.0 ' "$HERE/hosts") blocked domains"
echo "sha256:   $(shasum -a 256 "$HERE/hosts" | awk '{print $1}')"
echo "Record these in SOURCE."
