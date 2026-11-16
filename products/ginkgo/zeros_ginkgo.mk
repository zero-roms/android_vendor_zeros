#
# ZeroS for Xiaomi Redmi Note 8 (ginkgo)
#
# SPDX-License-Identifier: Apache-2.0
#
# The device layer (device/xiaomi/ginkgo, sm6125-common, kernel, blobs) is used
# unmodified. Everything ZeroS-specific comes from vendor/zeros.
#

ZEROS_BUILD := ginkgo

# LineageOS's version string expects the device codename in LINEAGE_BUILD,
# which its `breakfast` helper exports. We use plain `lunch`, so set it here.
LINEAGE_BUILD := $(ZEROS_BUILD)

# ZeroS common layer, inherited first so that it takes precedence over
# LineageOS where both define the same thing: product overlay directories are
# merged in inheritance order and the first listed wins (needed for the
# default wallpaper, which LineageOS also overlays; 24 October 2026).
$(call inherit-product, vendor/zeros/config/common.mk)

# Device layer, as LineageOS defines it
$(call inherit-product, device/xiaomi/ginkgo/lineage_ginkgo.mk)

# ginkgo is not A/B, so updates do not touch the recovery partition. This adds
# applypatch and its vendor_flash_recovery service, which writes
# /vendor/etc/recovery.img to the recovery partition when the Updater's "Update
# recovery" switch (persist.vendor.recovery_update) is on. Neither the ginkgo
# device tree nor LineageOS inherits it, so the switch did nothing (bug B23).
$(call inherit-product, $(SRC_TARGET_DIR)/product/non_ab_device.mk)

# ginkgo-only resource fixes (status bar insets for the rounded corners).
# Product overlays take precedence over the device tree's vendor overlays.
PRODUCT_PACKAGE_OVERLAYS += vendor/zeros/products/ginkgo/overlay

PRODUCT_NAME := zeros_ginkgo
