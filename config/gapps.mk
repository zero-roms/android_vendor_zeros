#
# SPDX-License-Identifier: Apache-2.0
#
# ZeroS Google build: the Google set, picked module by module from
# MindTheGapps (vendor/gapps, pinned in the manifest). Its arm64-vendor.mk is
# not inherited: the Android 17 package also installs the Google app, Family
# Link, TalkBack, Google Feedback and Exchange, which ZeroS leaves to the
# Play Store (ROM_PLAN.md, Phase 3A). Anything not listed here is never
# installed. Included from common.mk unless ZEROS_GAPPS=false.
#
# None of these adds a second Contacts, Calendar, Phone, Messages or Clock
# app: the sync adapters feed Google accounts into the existing apps.
#

PRODUCT_SOONG_NAMESPACES += \
    vendor/gapps/arm64 \
    vendor/gapps/common \
    vendor/gapps/overlay

# Play Services, Play Store, Google Services Framework
PRODUCT_PACKAGES += \
    com.google.android.gmssystem.prodvic \
    Phonesky \
    GoogleServicesFramework

# Google contacts and calendars in the existing Contacts and Etar apps
PRODUCT_PACKAGES += \
    GoogleContactsSyncAdapter \
    GoogleCalendarSyncAdapter

# First boot: Google sign-in, and restore from a Google backup or old phone
PRODUCT_PACKAGES += \
    SetupWizard \
    GoogleRestore \
    GooglePartnerSetup \
    d2d_cable_migration_feature.xml

# Voice typing and text to speech
PRODUCT_PACKAGES += \
    SpeechServicesByGoogle

# Removed in 0.6.2 (user's app review, 15 November 2026): Digital Wellbeing
# (Wellbeing, wellbeing.xml; about 33 MB while running; cannot be added later
# from the Play Store; Phase 4 plans ZeroS's own screen time page).

# Lets the Play Store install Android Auto if wanted (kept in the 15 November
# review although it runs at about 33 MB: without it Android Auto may not be
# installable at all)
PRODUCT_PACKAGES += \
    AndroidAutoStub

# Gboard, the Google build's keyboard (prebuilt/apps/Gboard)
PRODUCT_PACKAGES += \
    Gboard

# Google Messages, the Google build's SMS app (prebuilt/apps/GoogleMessages),
# replacing LineageOS's Messaging; the overlay makes it the default SMS app
PRODUCT_PACKAGES += \
    GoogleMessages
PRODUCT_PACKAGE_OVERLAYS += vendor/zeros/overlay-gapps

# Permissions, system config and overlays the above rely on
PRODUCT_PACKAGES += \
    allowed_apex_com.google.android.gmssystem.xml \
    default-permissions-google.xml \
    default-permissions-mtg.xml \
    zeros_gapps.rc \
    gms_fsverity_cert.der \
    google-hiddenapi-package-allowlist.xml \
    google.xml \
    privapp-permissions-google-product.xml \
    privapp-permissions-google-system_ext.xml \
    privapp-permissions-mtg.xml \
    sysconfig-mtg.xml \
    GmsOverlay \
    GmsSettingsOverlay \
    GmsSettingsProviderOverlay \
    GmsSetupWizardOverlay

# Left out on purpose: Velvet (Google app), FamilyLinkParentalControls,
# talkback, GoogleFeedback, PrebuiltExchange3Google,
# com.google.android.dialer.support, libjni_latinimegoogle (gesture typing
# for the AOSP keyboard, which the Google build replaces with Gboard).
# MindTheGapps' gapps.rc is replaced by prebuilt/gapps/zeros_gapps.rc, which
# drops ro.opa.eligible_device (bug B10).
