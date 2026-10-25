# ZeroS legal

ZeroS is an Android 17 build for the Xiaomi Redmi Note 8 (ginkgo), based on
LineageOS 24.0 and the Android Open Source Project.

Last updated 25 October 2026.

## Terms of use

ZeroS is free software, made as a hobby project. You may use, copy, change and
share it under the licences of its source code, listed below.

ZeroS comes as is, without any warranty. To install it you unlock the phone's
bootloader and replace the software the phone came with. Unlocking erases the
data on the phone and can void its warranty. A mistake during installation can
leave the phone unable to start. You install and use ZeroS at your own risk,
and as far as the law allows, the ZeroS developer is not liable for any damage
or loss of data that results.

Versions before 1.0 are test builds. Expect bugs, and keep a backup of anything
you cannot afford to lose.

## Licences

ZeroS is built from open source code. Most of it, including Android and
LineageOS, is under the Apache License 2.0. The Linux kernel is under version 2
of the GNU General Public License. Settings > About phone > Legal information >
Third-party licences lists the licence of every part of the system. The source
code is on GitHub at https://github.com/zero-roms.

The Google build includes Google Play services, the Play Store, Gboard and
other Google apps. They are Google's software, not part of ZeroS, and Google's
terms apply to them: https://policies.google.com/terms. The other apps that
come with ZeroS (Cromite, Fossify Gallery, Fossify File Manager and NotallyX)
keep their own licences.

Android is a trademark of Google LLC. LineageOS, Xiaomi and Redmi are
trademarks of their owners. None of them made, endorsed or supports ZeroS.

## Privacy

This part covers the data that ZeroS itself sends. Apps you install, and the
Google apps in the Google build, send their own data under their own privacy
policies. Google's is at https://policies.google.com/privacy.

ZeroS contains no ads or trackers. The ZeroS developer does not sell the data
described here and does not share it with anyone.

### Update checks

The Updater (Settings > System > Updater) asks the ZeroS update server whether
a new version is out, and downloads it when you choose to install it. The
request contains the phone model but no ID for you or the phone. The update
server is a Google Cloud Storage bucket. ZeroS keeps no log of these requests,
and Google handles them under its own privacy policy.

### ZeroS statistics

ZeroS statistics is off unless you switch it on in Settings > Security &
privacy > More security & privacy > Trust > ZeroS statistics. While it is on,
the phone sends one short report a day containing:

- an ID made from the phone's Android ID with a one-way hash, so the Android ID
  itself is never sent
- the phone model
- the build version
- a country code, taken from the mobile network or, without one, from the
  phone's language setting
- the name and code of the mobile network

Preview data, on the same screen, shows exactly what the phone sends. ZeroS
uses these reports only to count how many phones run each build. The server
deletes each report 13 months after it arrives.

### Bug reports

A bug report leaves the phone only when you tap Send to ZeroS on the bug report
screen. It contains the phone's system logs and settings, the list of installed
apps and other details about how the phone is set up and what it was doing. It
can include personal information, such as account names and the names of Wi-Fi
networks. What you type under "What went wrong?" goes with it, along with the
phone model and the ZeroS version.

ZeroS stores bug reports in a private Google Cloud Storage bucket in the United
States. Only the ZeroS developer can read them, and only to find and fix the
problem they describe. The server deletes each report 30 days after it
arrives. After sending, the screen shows a report ID. Quote it if you open an
issue or ask for the report to be deleted.

Do not attach a bug report to a public GitHub issue. Anyone can download it
there.

### Server logs

The server that receives statistics and bug reports runs on Google Cloud Run.
Google records the IP address and time of each request to it and keeps that
record for 30 days. ZeroS looks at it only to keep the server working and to
block abuse.

### Connections Android makes itself

Like other Android phones, ZeroS contacts Google's servers for a few system
functions, for example to check whether a Wi-Fi network needs a sign-in page,
to set the clock and to help GPS find a position faster.

### Your choices

You can switch ZeroS statistics off at any time in the same place, and the
phone stops sending reports. To have a bug report or your statistics deleted
before the dates above, email promptandchai@gmail.com with the report ID, or,
for statistics, the Unique ID shown in Preview data. The ZeroS developer
deletes it within seven days and replies to confirm.

### Changes to this page

When this page changes, the new version appears here with a new date, and the
ZeroS changelog says what changed. Earlier versions stay in this file's history
on GitHub.

## Contact

Email promptandchai@gmail.com, or open an issue at
https://github.com/zero-roms/android_vendor_zeros/issues.

## Credits

ZeroS is based on LineageOS (https://lineageos.org) and the Android Open Source
Project (https://source.android.com). LineageOS's own legal page, which covers
LineageOS's website and services, is at https://lineageos.org/legal.
