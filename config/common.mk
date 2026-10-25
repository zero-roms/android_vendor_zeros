#
# ZeroS common configuration, inherited by every ZeroS product makefile.
#
# SPDX-License-Identifier: Apache-2.0
#
# Phase 1 skeleton: identity only. App set, tuning, modes and privacy features
# arrive in later phases, each as its own file included from here.
#

include vendor/zeros/config/version.mk

# Identity visible to apps and in Settings > About phone
PRODUCT_SYSTEM_PROPERTIES += \
    ro.zeros.version=$(ZEROS_VERSION) \
    ro.zeros.semver=$(ZEROS_SEMVER) \
    ro.zeros.build.date=$(ZEROS_BUILD_DATE) \
    ro.zeros.build.type=$(ZEROS_BUILDTYPE) \
    ro.zeros.device=$(ZEROS_BUILD) \
    ro.zeros.display.version=ZeroS-$(ZEROS_SEMVER)

# Update server for LineageOS's Updater (lineage.updater.uri, HTTPS only; see
# build/tools/publish-ota.sh). During 3B-3C updates come from an unlisted
# Cloud Storage bucket, so the address is supplied only in the build
# environment (ZEROS_UPDATER_URI) and never committed. Without it the Updater
# asks LineageOS's server, which offers nothing for an UNOFFICIAL build.
# lineage.updater.uri is not a ro. property, so Android limits it to 91 bytes
# (gen_build_prop fails the build otherwise).
ifneq ($(ZEROS_UPDATER_URI),)
PRODUCT_SYSTEM_EXT_PROPERTIES += \
    lineage.updater.uri=$(ZEROS_UPDATER_URI)
endif

# Settings > About phone shows ro.zeros.version in its own "ZeroS version" row
# (ZeroS fork of Settings, from 0.5.0); LineageOS's version row is not shown
# (from 0.5.1). 0.2.0-0.4.0 put "ZeroS-<version>" into LineageOS's version
# string instead (TARGET_UNOFFICIAL_BUILD_ID).

# Boot animation: design B1 "orbit" in black, white and red (chosen 24 October
# 2026). LineageOS's bootanimation.zip module copies this file instead of
# generating its own (vendor/lineage/bootanimation, prebuilt_file hook); the
# dark-theme variant is a link to the same file. Rebuild with
# bootanimation/make-bootanimation.sh.
TARGET_BOOTANIMATION := vendor/zeros/bootanimation/bootanimation.zip

# Resource overlays shared by every ZeroS device
PRODUCT_PACKAGE_OVERLAYS += vendor/zeros/overlay

# Apps removed from the LineageOS set (see ROM_PLAN.md cut list).
PRODUCT_PACKAGES += \
    ZeroSRemovedPackages

# ZeroS's own system app: the Bug report tile and screen (send to ZeroS, save,
# share), Android's bug report handler and "Save to Downloads" in the share
# sheet. Bug reports and ZeroS statistics go to server/reports. The handler
# switch is in overlay/frameworks/base/core/res; statistics are LineageParts'
# with ZeroS's text and server (overlay/packages/apps/LineageParts).
PRODUCT_PACKAGES += \
    ZeroSTools

# Third-party apps, built from source (prebuilt/apps/build-fossify.sh,
# prebuilt/apps/build-notallyx.sh)
PRODUCT_PACKAGES += \
    FossifyFileManager \
    FossifyGallery \
    NotallyX

# Third-party apps kept with their publishers' signatures; the APKs are not in
# git and are put in place by prebuilt/apps/fetch-prebuilts.sh. Cromite
# replaces Jelly.
PRODUCT_PACKAGES += \
    Cromite

# Google build (Phase 3A). Build with ZEROS_GAPPS=false for the vanilla
# variant without any Google software (Phase 3D).
ZEROS_GAPPS ?= true
ifeq ($(ZEROS_GAPPS),true)
$(call inherit-product, vendor/zeros/config/gapps.mk)
endif
