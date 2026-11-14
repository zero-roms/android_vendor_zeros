# ZeroS remote library

The remote library preloaded for Nope Remote (0.6.1): `noperemote-library.zip`,
a zip of Flipper `.ir` files laid out as `<type>/<brand>/<model>.ir`, copied to
`/product/etc/noperemote/` with `NOTICE.txt` (sources and licences, shown in
Nope Remote's Settings). ZeroS's Nope Remote (zero-roms/nope-remote, branch
zeros) reads it in place as the "ZeroS library" source.

Built on the Mac from three libraries at pinned commits (fetch-sources.sh):

| Library | Licence | Used |
|---|---|---|
| Flipper Devices IRDB | MIT | all remotes |
| IREXT | MIT | remotes with a brand (its set-top boxes are listed by Chinese cable operator instead) |
| Flipper-IRDB | CC0 1.0 for files added after commit 2319685 (7 August 2025) | only those files, listed in flipper-irdb-cc0-files.txt; the rest has no licence |

Air conditioner remotes are left out until the full AC remote (Phase 4).

build-library.py writes every button as raw timings. Buttons the libraries
store as protocol, address and command are encoded by irtool, a small filter
around Flipper Zero's own infrared encoders and decoders (lib/infrared from the
Flipper firmware, GPL-3.0; built and run on the Mac only, never shipped). The
app then sends every protocol through its raw path; its own protocol code
covers only some of them. Duplicate remotes are removed as described in
build-library.py and ROM_PLAN.md (3C); report.txt has the counts.

## Rebuild

    ./fetch-sources.sh ~/rom/zeros/src/irdb/fetched
    ./build.sh ~/rom/zeros/src/irdb/fetched

The same inputs give the same zip (fixed dates, sorted entries); compare the
checksum with report.txt. To move to newer library versions, change the
commits in fetch-sources.sh (and regenerate flipper-irdb-cc0-files.txt from
GitHub's compare of 2319685 with the new Flipper-IRDB commit, added files
only), rebuild, and check report.txt before committing.
