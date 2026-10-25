#
# ZeroS version
#
# SPDX-License-Identifier: Apache-2.0
#
# ZEROS_BUILD is the device codename, set by the product makefile before this
# file is read. ZEROS_BUILDTYPE may be set in the environment: UNOFFICIAL
# (default, local builds), EXPERIMENTAL, or RELEASE.
#

# Included early by each product makefile (LineageOS's version string needs
# ZEROS_SEMVER) and again from common.mk; evaluate once.
ifndef ZEROS_VERSION_MK_INCLUDED
ZEROS_VERSION_MK_INCLUDED := true

ZEROS_VERSION_MAJOR := 0
ZEROS_VERSION_MINOR := 5
ZEROS_VERSION_PATCH := 1

ZEROS_BUILD_DATE := $(shell date -u +%Y%m%d)

ifndef ZEROS_BUILDTYPE
    ZEROS_BUILDTYPE := UNOFFICIAL
endif
ifeq ($(filter RELEASE EXPERIMENTAL UNOFFICIAL,$(ZEROS_BUILDTYPE)),)
    ZEROS_BUILDTYPE := UNOFFICIAL
endif

ZEROS_SEMVER  := $(ZEROS_VERSION_MAJOR).$(ZEROS_VERSION_MINOR).$(ZEROS_VERSION_PATCH)
ZEROS_VERSION := $(ZEROS_SEMVER)-$(ZEROS_BUILD_DATE)-$(ZEROS_BUILDTYPE)-$(ZEROS_BUILD)

endif # ZEROS_VERSION_MK_INCLUDED
