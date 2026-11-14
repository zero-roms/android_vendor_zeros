#!/usr/bin/env python3
"""
Build ZeroS's preloaded remote library for Nope Remote (Phase 3C, 0.6.1).

Merges three IR code libraries into one zip of Flipper .ir files laid out as
<type>/<brand>/<model>.ir, removing duplicate remotes:

  Flipper Devices IRDB (MIT)        database/categories/<type>/<brand>/<model>/
  Flipper-IRDB (CC0 part only)      the files in flipper-irdb-cc0-files.txt
  IREXT (MIT)                       the SQLite database, remotes with a brand

Every button is written as raw timings. Buttons the libraries store as
protocol, address and command are encoded by irtool (Flipper's own encoders),
so the app sends every protocol correctly through its raw path.

Duplicates (ROM_PLAN.md, 3C): remotes are compared within the same type and
brand. A remote is dropped when every one of its button signals is also in a
remote that is kept. Larger remotes are kept first; ties go to remotes the
library stored as decoded protocols, then remotes with a model name, then the
source order Flipper Devices IRDB, Flipper-IRDB, IREXT. Signals are compared
by protocol, address and command where Flipper's decoders read them, and by
their first frame scaled to its shortest pulse, so the same code captured or
encoded with slightly different timings still matches.

  python3 -I build-library.py <IRDB> <Flipper-IRDB> <irext .db> <irtool> <out dir>

Writes <out dir>/noperemote-library.zip and <out dir>/report.txt.

SPDX-License-Identifier: Apache-2.0
"""
import collections
import hashlib
import io
import math
import os
import re
import sqlite3
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = ["Flipper Devices IRDB", "Flipper-IRDB", "IREXT"]

# Source category -> ZeroS type. None: not preloaded (air conditioners need the
# full AC remote planned for Phase 4).
TYPES = {
    # Flipper Devices IRDB
    "A_V_receiver": "Audio", "Air_Purifiers": "Air purifier", "Box": "Set-top box",
    "Camera": "Camera", "DVD": "DVD and Blu-ray", "Fan": "Fan", "Projector": "Projector",
    "TVs": "TV",
    # Flipper-IRDB
    "ACs": None, "Audio_and_Video_Receivers": "Audio", "SoundBars": "Audio",
    "Speakers": "Audio", "CD_Players": "Audio", "Projectors": "Projector", "Fans": "Fan",
    "LED_Lighting": "Light", "Cable_Boxes": "Set-top box", "Streaming_Devices": "Set-top box",
    "DVB-T": "Set-top box", "TV_Tuner": "Set-top box", "Blu-Ray": "DVD and Blu-ray",
    "DVD_Players": "DVD and Blu-ray", "Vacuum_Cleaners": "Vacuum cleaner", "Cameras": "Camera",
    # IREXT
    "AC": None, "Air Cleaner": "Air purifier", "BOX": "Set-top box", "Cleaning Robot": "Vacuum cleaner",
    "Dyson": "Fan", "FAN": "Fan", "IPTV": "Set-top box", "Light": "Light", "PROJECTOR": "Projector",
    "STB": "Set-top box", "STEREO": "Audio", "TV": "TV",
}

# Brand names: words dropped from the end before comparing, and spellings that
# name the same brand.
BRAND_SUFFIXES = {"electronics", "electronic", "electric", "corporation", "corp", "co", "ltd",
                  "limited", "inc", "international", "intl", "group", "tv"}
BRAND_ALIASES = {"lgelectronics": "lg", "hewlettpackard": "hp", "anthemav": "anthem",
                 "curtismathis": "curtismathes", "mitsubushi": "mitsubishi", "royalsta": "royalstar",
                 "sumavison": "sumavision", "technic": "technics"}

# Spellings shown for merged brands, where the most used one is a misspelling
BRAND_DISPLAY = {"mitsubishi": "Mitsubishi", "royalstar": "Royalstar", "sumavision": "Sumavision",
                 "curtismathes": "Curtis Mathes", "bellhowell": "Bell & Howell",
                 "bowerswilkins": "Bowers & Wilkins"}

MIN_TIMING_US = 50          # Android's IR service rejects shorter pulses (bug B9)
MAX_PATTERN_US = 2_000_000  # and patterns longer than two seconds


def irtool(path, lines):
    out = subprocess.run([path], input="".join(lines), capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def parse_ir(text):
    """Buttons of a Flipper .ir file: (name, ("parsed", protocol, address, command)) or
    (name, ("raw", frequency, timings))."""
    buttons, cur = [], {}

    def flush():
        if "name" in cur:
            if cur.get("type") == "parsed" and "protocol" in cur and "command" in cur:
                le = lambda s: sum(int(b, 16) << (8 * i) for i, b in enumerate(s.split()[:4]))
                buttons.append((cur["name"], ("parsed", cur["protocol"], le(cur.get("address", "0")),
                                              le(cur["command"]))))
            elif cur.get("type") == "raw" and "data" in cur:
                t = [int(x) for x in cur["data"].split() if x.lstrip("-").isdigit()]
                buttons.append((cur["name"], ("raw", int(cur.get("frequency", "38000") or 38000), t)))
        cur.clear()

    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            flush()
            continue
        k, _, v = s.partition(":")
        if k in ("name", "type", "protocol", "address", "command", "frequency", "data"):
            if k == "name" and "name" in cur:
                flush()
            cur[k] = v.strip()
    flush()
    return buttons


def signature(t):
    """First frame of a signal, each pulse as a multiple of the frame's shortest pulse
    (log-scale buckets for long ones), so small timing differences compare equal."""
    frame = []
    for i, d in enumerate(t):
        if i % 2 == 1 and d >= 8000 and len(frame) >= 8:
            break
        frame.append(d)
    if len(frame) < 4:
        return None
    m = min(frame)
    small = sorted(d for d in frame if d <= 1.4 * m)
    unit = small[len(small) // 2]
    return tuple(round(r) if r < 6.5 else 100 + round(math.log(r) / math.log(1.15))
                 for r in (d / unit for d in frame))


def brand_key(b):
    words = [w for w in re.sub(r"[^a-z0-9]+", " ", b.lower()).split() if w != "and"]
    while len(words) > 1 and words[-1] in BRAND_SUFFIXES:
        words.pop()
    k = "".join(words)
    return BRAND_ALIASES.get(k, k)


def clean_name(s):
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "-", s.replace("_", " "))
    return re.sub(r"\s+", " ", s).strip(" .") or "Remote"


class Remote:
    def __init__(self, source, category, brand, model, origin, buttons, has_model):
        self.source, self.category, self.brand, self.model = source, category, brand, model
        self.origin, self.buttons, self.has_model = origin, buttons, has_model
        self.type = TYPES.get(category, clean_name(category))
        self.decoded = sum(1 for _, s in buttons if s[0] == "parsed") * 2 >= max(1, len(buttons))


def load_irdb(root):
    base = os.path.join(root, "database", "categories")
    out = []
    dirs = lambda d: sorted(x for x in os.listdir(d) if not x.startswith(".") and os.path.isdir(os.path.join(d, x)))
    for cat in dirs(base):
        for brand in dirs(os.path.join(base, cat)):
            bdir = os.path.join(base, cat, brand)
            for model in dirs(bdir):
                for f in sorted(os.listdir(os.path.join(bdir, model))):
                    if f.endswith(".ir"):
                        p = os.path.join(bdir, model, f)
                        out.append(Remote(SOURCES[0], cat, brand, f[:-3], os.path.relpath(p, root),
                                          parse_ir(open(p, encoding="utf-8", errors="replace").read()), True))
    return out


def load_flipper_irdb(root):
    out = []
    for line in open(os.path.join(HERE, "flipper-irdb-cc0-files.txt"), encoding="utf-8"):
        rel = line.strip()
        if not rel or rel.startswith("#"):
            continue
        parts = rel.split("/")
        if len(parts) < 3:
            continue
        p = os.path.join(root, rel)
        out.append(Remote(SOURCES[1], parts[0], parts[1], os.path.splitext(parts[-1])[0], rel,
                          parse_ir(open(p, encoding="utf-8", errors="replace").read()), True))
    return out


def load_irext(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute("""
        SELECT ri.id, c.name_en, b.name_en, ri.remote, dr.key_name, dr.key_value
        FROM decode_remote dr JOIN remote_index ri ON dr.remote_index_id = ri.id
        JOIN brand b ON ri.brand_id = b.id JOIN category c ON ri.category_id = c.id
        WHERE dr.key_name IS NOT NULL AND length(dr.key_name) > 0
        ORDER BY ri.id, dr.id""")
    remotes = collections.OrderedDict()
    for rid, cat, brand, remote, key, value in rows:
        if TYPES.get(cat, "") is None:
            continue
        r = remotes.get(rid)
        if r is None:
            num = re.sub(r"^\D*", "", remote or "") or str(rid)
            r = remotes[rid] = Remote(SOURCES[2], cat, brand, f"Code {num}", f"remote_index {rid} ({remote})", [], False)
        t = [int(x) for x in (value or "").split(",") if x.strip().isdigit()]
        if t:
            r.buttons.append((key, ("raw", 38000, t)))
    con.close()
    return list(remotes.values())


def main():
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    irdb, flipper, irext_db, tool, outdir = sys.argv[1:]
    remotes = [r for r in load_irdb(irdb) + load_flipper_irdb(flipper) + load_irext(irext_db) if r.type]

    # Encode every parsed button with Flipper's encoders
    reqs = [(r, i, s) for r in remotes for i, (_, s) in enumerate(r.buttons) if s[0] == "parsed"]
    answers = irtool(tool, [f"E {s[1]} {s[2]:X} {s[3]:X}\n" for _, _, s in reqs])
    encoded = {}
    for (r, i, s), a in zip(reqs, answers):
        f = a.split()
        encoded[(id(r), i)] = ("raw", int(f[0]), [int(x) for x in f[2:]]) if f and f[0] != "ERR" else None

    stats = collections.Counter()
    for r in remotes:
        kept, names = [], set()
        for i, (name, s) in enumerate(r.buttons):
            if s[0] == "parsed":
                s = encoded[(id(r), i)]
                if s is None:
                    stats["buttons: unknown protocol"] += 1
                    continue
            t = s[2]
            if not any(t):
                stats["buttons: no code (empty in the library)"] += 1
                continue
            if min(t) < MIN_TIMING_US or sum(t) > MAX_PATTERN_US:
                stats["buttons: timings Android cannot send"] += 1
                continue
            if name.lower() in names:
                stats["buttons: repeated name in a remote"] += 1
                continue
            names.add(name.lower())
            kept.append((name, s[1], t, signature(t)))
        r.raw = kept

    # Each button is known by its timing shape and, where Flipper's decoders read it,
    # by protocol, address and command; two buttons match when either agrees.
    flat = [(r, b) for r in remotes for b in r.raw]
    decoded = irtool(tool, ["D " + " ".join(map(str, b[2])) + "\n" for _, b in flat])
    for r in remotes:
        r.keys = []
    for (r, b), d in zip(flat, decoded):
        k = {("t",) + b[3]} if b[3] is not None else set()
        if d != "NONE":
            k.add(("p",) + tuple(d.split()))
        if k:
            r.keys.append(frozenset(k))
    for r in remotes:
        r.sigs = frozenset(r.keys)
        r.all = frozenset().union(*r.keys) if r.keys else frozenset()

    # Brand display names: the most used spelling, Flipper sources first on ties
    spellings = collections.defaultdict(collections.Counter)
    for r in remotes:
        spellings[brand_key(r.brand)][clean_name(r.brand)] += 3 - SOURCES.index(r.source)
    brand_name = {k: max(c.items(), key=lambda kv: (kv[1], not kv[0].islower(), kv[0]))[0]
                  for k, c in spellings.items()}
    brand_name.update((k, v) for k, v in BRAND_DISPLAY.items() if k in brand_name)

    groups = collections.defaultdict(list)
    for r in remotes:
        if r.sigs:
            groups[(r.type, brand_key(r.brand))].append(r)
        else:
            stats["remotes: no usable buttons"] += 1

    before = collections.Counter((r.type, r.source) for r in remotes)
    after = collections.Counter()
    keep = []
    for (typ, bk), rs in sorted(groups.items()):
        rs.sort(key=lambda r: (-len(r.sigs), not r.decoded, not r.has_model, SOURCES.index(r.source), r.origin))
        kept = []
        for r in rs:
            if any(all(b & k.all for b in r.sigs) for k in kept):
                continue
            kept.append(r)
        for r in kept:
            after[(typ, r.source)] += 1
            keep.append((typ, brand_name[bk], r))

    # Write the zip: fixed dates and sorted entries, so the same inputs give the same file
    os.makedirs(outdir, exist_ok=True)
    zpath = os.path.join(outdir, "noperemote-library.zip")
    files, used = [], set()
    for typ, brand, r in keep:
        base = f"{clean_name(typ)}/{brand}/{clean_name(r.model)}"
        path, n = base + ".ir", 2
        while path.lower() in used:
            path, n = f"{base} ({n}).ir", n + 1
        used.add(path.lower())
        body = io.StringIO()
        body.write(f"Filetype: IR signals file\nVersion: 1\n# ZeroS remote library: {r.source}, {r.origin}\n")
        for name, freq, t, _ in r.raw:
            body.write(f"# \nname: {name}\ntype: raw\nfrequency: {freq}\nduty_cycle: 0.330000\n"
                       f"data: {' '.join(map(str, t))}\n")
        body.write("#\n")
        files.append((path, body.getvalue().encode("utf-8")))
    files.sort()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path, data in files:
            zi = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type, zi.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
            z.writestr(zi, data)

    # Report
    rep = io.StringIO()
    types = sorted({t for t, _ in before})
    rep.write("Remotes per type and source, before -> after removing duplicates\n\n")
    rep.write(f"{'type':18}" + "".join(f"{s:>24}" for s in SOURCES) + f"{'total':>16}\n")
    for t in types + ["All"]:
        sel = (lambda c, s: sum(v for (tt, ss), v in c.items() if ss == s and (t == "All" or tt == t)))
        rep.write(f"{t:18}" + "".join(f"{sel(before, s):>11} -> {sel(after, s):<9}" for s in SOURCES)
                  + f"{sum(sel(before, s) for s in SOURCES):>8} -> {sum(sel(after, s) for s in SOURCES)}\n")
    rep.write("\nLeft out\n")
    for k, v in sorted(stats.items()):
        rep.write(f"  {k}: {v}\n")
    raw_size = sum(len(d) for _, d in files)
    sha = hashlib.sha256(open(zpath, "rb").read()).hexdigest()
    rep.write(f"\n{len(files)} remotes, {sum(len(r.raw) for _, _, r in keep)} buttons, "
              f"{raw_size / 1e6:.1f} MB of .ir text, zip {os.path.getsize(zpath) / 1e6:.1f} MB\n"
              f"sha256 {sha}  noperemote-library.zip\n")
    open(os.path.join(outdir, "report.txt"), "w").write(rep.getvalue())
    print(rep.getvalue(), end="")


if __name__ == "__main__":
    main()
