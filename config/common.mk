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

# Settings > About phone > Legal information > ZeroS legal (ZeroS fork of
# Settings, from 0.5.1) opens ZeroS's terms and privacy policy.
PRODUCT_SYSTEM_PROPERTIES += \
    ro.zeros.legal.url=https://github.com/zero-roms/android_vendor_zeros/blob/zeros-24.0/LEGAL.md

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
# The file name carries its checksum (make-bootanimation.sh): LineageOS's
# genrule only rebuilds when this path changes (bug B17).
TARGET_BOOTANIMATION := vendor/zeros/bootanimation/bootanimation-8f5a0dce.zip

# Resource overlays shared by every ZeroS device
PRODUCT_PACKAGE_OVERLAYS += vendor/zeros/overlay

# Apps removed from the LineageOS set (see ROM_PLAN.md cut list).
PRODUCT_PACKAGES += \
    ZeroSRemovedPackages

# ZeroS's own system app: the Bug report tile and screen (send to ZeroS, save,
# share), Android's bug report handler and "Save to Downloads" in the share
# sheet. Bug reports and ZeroS statistics go to server/reports. The handler
# switch is in overlay/frameworks/base/core/res; statistics come from ZeroS's
# copy of LineageParts, with ZeroS's text and server (from 0.5.2).
PRODUCT_PACKAGES += \
    ZeroSTools

# Ad and tracker blocking (0.6.0): the blocklist, its licence and the boot
# rule that lays it over /system/etc/hosts (adblock/zeros-adblock.rc, which
# needs the one SELinux rule in sepolicy/private). The on/off switch is the Ad
# blocking tile in ZeroS's LineageParts (persist.sys.zeros.adblock).
PRODUCT_COPY_FILES += \
    vendor/zeros/adblock/hosts:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/zeros/hosts \
    vendor/zeros/adblock/LICENSE-StevenBlack-hosts:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/zeros/hosts.LICENSE \
    vendor/zeros/adblock/zeros-adblock.rc:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/init/zeros-adblock.rc
PRODUCT_PRIVATE_SEPOLICY_DIRS += vendor/zeros/sepolicy/private

# Third-party apps, built from source (prebuilt/apps/build-fossify.sh,
# prebuilt/apps/build-notallyx.sh, prebuilt/apps/build-noperemote.sh)
PRODUCT_PACKAGES += \
    FossifyFileManager \
    FossifyGallery \
    NopeRemote \
    NotallyX

# Nope Remote's preloaded remote library and its sources and licences (0.6.1;
# noperemote/library, read in place by ZeroS's Nope Remote)
PRODUCT_COPY_FILES += \
    vendor/zeros/noperemote/library/noperemote-library.zip:$(TARGET_COPY_OUT_PRODUCT)/etc/noperemote/noperemote-library.zip \
    vendor/zeros/noperemote/library/NOTICE.txt:$(TARGET_COPY_OUT_PRODUCT)/etc/noperemote/NOTICE.txt

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
