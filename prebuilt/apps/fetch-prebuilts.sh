#!/bin/bash
#
# Put the prebuilt APKs that are not kept in git in place, and check each
# against the SHA-256 (and, where pinned, the signing certificate) in its
# SOURCE file. Run before every build, from the top of the source tree:
#
#   vendor/zeros/prebuilt/apps/fetch-prebuilts.sh
#
# Cromite is downloaded from its GitHub release when missing. Gboard is not
# downloadable by script: copy Gboard.apk from the Mac to
# vendor/zeros/prebuilt/apps/Gboard/ first (HANDBOOK.md). Both stay out of git
# (.gitignore). Every build needs both files, the vanilla build included,
# because Soong reads every module in the tree.
#
# SPDX-License-Identifier: Apache-2.0
#

set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)

field() { sed -n "s/^$2: *//p" "$HERE/$1/SOURCE" | head -n1; }

sha256() {
    if command -v sha256sum >/dev/null; then sha256sum "$1" | awk '{print $1}'
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}

find_apksigner() {
    for c in "${APKSIGNER:-}" apksigner out/host/linux-x86/bin/apksigner; do
        [ -n "$c" ] && command -v "$c" >/dev/null 2>&1 && { echo "$c"; return; }
    done
}

check() {
    local app=$1 apk=$2
    local file="$HERE/$app/$apk"
    local want; want=$(field "$app" sha256)
    case "$want" in
        ""|TO\ PIN*) echo "error: $app/SOURCE has no pinned sha256 yet" >&2; return 1 ;;
    esac
    local got; got=$(sha256 "$file")
    if [ "$got" != "$want" ]; then
        echo "error: $app/$apk sha256 $got, expected $want" >&2
        return 1
    fi
    local cert; cert=$(field "$app" cert)
    if [ -n "$cert" ] && [ "${cert#TO PIN}" = "$cert" ]; then
        local signer; signer=$(find_apksigner || true)
        if [ -n "$signer" ]; then
            "$signer" verify --print-certs "$file" | grep -qi "SHA-256 digest: $cert" || {
                echo "error: $app/$apk is not signed with the pinned certificate" >&2
                return 1
            }
        else
            echo "warning: apksigner not found, $app certificate not checked here" >&2
        fi
    fi
    echo "ok: $app/$apk ($got)"
}

# Cromite: download when missing
cromite="$HERE/Cromite/Cromite.apk"
if [ ! -f "$cromite" ]; then
    url=$(field Cromite url)
    echo "Downloading Cromite from $url"
    curl -fL --retry 3 -o "$cromite.part" "$url"
    mv "$cromite.part" "$cromite"
fi
check Cromite Cromite.apk

# Gboard: copied from the Mac
if [ ! -f "$HERE/Gboard/Gboard.apk" ]; then
    echo "error: vendor/zeros/prebuilt/apps/Gboard/Gboard.apk is missing;" \
         "copy it from the Mac (HANDBOOK.md)" >&2
    exit 1
fi
check Gboard Gboard.apk

if [ ! -f "$HERE/GoogleMessages/GoogleMessages.apk" ]; then
    echo "error: vendor/zeros/prebuilt/apps/GoogleMessages/GoogleMessages.apk is missing;" \
         "copy it from the Mac (HANDBOOK.md)" >&2
    exit 1
fi
check GoogleMessages GoogleMessages.apk
