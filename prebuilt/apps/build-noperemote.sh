#!/bin/bash
#
# Build Nope Remote, the IR remote app ZeroS ships, from ZeroS's fork and place
# the APK where prebuilt/apps/NopeRemote/Android.bp expects it. The ROM build
# signs it with its default app key.
#
# SPDX-License-Identifier: Apache-2.0
#
# Usage: build-noperemote.sh <dir-with-sources>
#   <dir-with-sources> holds the clone nope-remote/ of
#   github.com/zero-roms/nope-remote, checked out at the commit pinned below
#   (branch zeros: upstream monuk7735/nope-remote 67549e32, 1 November 2026,
#   plus ZeroS's changes: bug B9 fixes and the preloaded ZeroS library, read
#   from /product/etc/noperemote, see vendor/zeros/noperemote/library).
#
# Needs: JDK 17 (JAVA_HOME; the project's Kotlin toolchain asks for exactly 17,
# e.g. Eclipse Temurin 17), Android SDK with platform 36 (ANDROID_HOME),
# network for Gradle's first run.
#
# The release build has no signing key, so Gradle writes an unsigned APK.
# There is no upstream APK to compare with: ZeroS's build has its own changes.
#

set -euo pipefail

SRC=${1:?usage: build-noperemote.sh <dir-with-sources>}
HERE=$(cd "$(dirname "$0")" && pwd)

NAME=NopeRemote
DIR=nope-remote
UPSTREAM=67549e32ee48862ff60d7b42f174f0f43f6532de
COMMIT=4d7d0d722e5008c152a758312b60af167b9e0304

: "${JAVA_HOME:?set JAVA_HOME to a JDK 17}"
: "${ANDROID_HOME:?set ANDROID_HOME to the Android SDK}"

repo="$SRC/$DIR"
echo "==> $NAME ($DIR @ $COMMIT)"
head=$(git -C "$repo" rev-parse HEAD)
if [ "$head" != "$COMMIT" ]; then
    echo "error: $repo is at $head, expected $COMMIT" >&2; exit 1
fi
if [ -n "$(git -C "$repo" status --porcelain)" ]; then
    echo "error: $repo has local changes" >&2; exit 1
fi

# Point Gradle's toolchain lookup at JAVA_HOME and stop it downloading a JDK.
(cd "$repo" && ./gradlew --no-daemon --max-workers=4 -q \
    -Porg.gradle.java.installations.paths="$JAVA_HOME" \
    -Porg.gradle.java.installations.auto-download=false \
    assembleRelease)

apk="$repo/app/build/outputs/apk/release/app-release-unsigned.apk"
mkdir -p "$HERE/$NAME"
cp "$apk" "$HERE/$NAME/$NAME.apk"
sum=$(shasum -a 256 "$HERE/$NAME/$NAME.apk" | awk '{print $1}')

cat > "$HERE/$NAME/SOURCE" <<EOT
app:     $NAME
source:  https://github.com/zero-roms/nope-remote (branch zeros)
commit:  $head
based on: https://github.com/monuk7735/nope-remote at $UPSTREAM (v2.6 plus fixes, 1 November 2026)
build:   release, unsigned (signed by the ROM build)
sha256:  $sum
built:   $(date -u +%Y-%m-%dT%H:%MZ) with $("$JAVA_HOME/bin/java" -version 2>&1 | head -n1)
EOT
echo "    $sum"
