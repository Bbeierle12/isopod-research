# -*- coding: utf-8 -*-
"""Cross-match every Isopoda species note against WoRMS and record the result.

The vault's species tree comes from the GBIF backbone, but the taxonomic
authority for Isopoda is WoRMS (the World List of Marine, Freshwater and
Terrestrial Isopod Crustaceans). Until now a note asserted acceptance simply by
existing. This script records what WoRMS actually says, per species:

    worms_aphia_id     the AphiaID of the matched record
    worms_status       accepted | unaccepted | synonym | nomen dubium | ...
    worms_accepted     the currently accepted name, when it differs
    authorship         backfilled from WoRMS when GBIF's string lacked a year

Results are cached to data/worms_species.json, so the crawl is resumable and a
re-run costs nothing. Writing to notes is a separate step (--write), so the
network pass and the vault edit can be reviewed independently.

Python 3.9+.  Run:
    python scripts/worms_match.py --fetch          # populate/refresh the cache
    python scripts/worms_match.py --write          # apply the cache to notes
    python scripts/worms_match.py --report         # summarise the cache
"""
import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

import _vault as V

REST = "https://www.marinespecies.org/rest"
UA = {"User-Agent": "isopod-research/1.0 (+https://github.com/bbeierle12/isopod-research)"}
CACHE = V.DATA / "worms_species.json"
BATCH = 40
_YEAR = re.compile(r"\b(1[6-9]\d\d|20[0-2]\d)\b")


def get(url, attempts=4):
    for a in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return None if r.status == 204 else json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (204, 404):
                return None
            if a == attempts - 1:
                raise
            time.sleep(2 ** a)
        except Exception:
            if a == attempts - 1:
                raise
            time.sleep(2 ** a)


def vault_species():
    """{scientificName: [note paths]} for every species note."""
    out = {}
    for note in V.ISOPODA.rglob("*.md"):
        if note.name.startswith("_"):
            continue
        parsed = V.parse_frontmatter(V.read_text(note))
        if not parsed:
            continue
        m = re.search(r"^scientificName:[ \t]*(.*)$", parsed[1], re.M)
        name = (m.group(1).strip().strip('"') if m else note.stem)
        out.setdefault(name, []).append(note)
    return out


def pick(records):
    """Choose the species-rank record; prefer an accepted one."""
    sp = [r for r in records if r.get("rank") == "Species"] or records
    acc = [r for r in sp if r.get("status") == "accepted"]
    return (acc or sp)[0] if sp else None


def fetch(names, cache):
    todo = [n for n in names if n not in cache]
    print("cached: %d | to fetch: %d" % (len(cache), len(todo)))
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        q = "&".join("scientificnames[]=%s" % urllib.parse.quote(n) for n in chunk)
        try:
            out = get("%s/AphiaRecordsByNames?%s&marine_only=false" % (REST, q))
        except Exception as e:
            print("  batch failed (%s) — leaving uncached, re-run to retry" % e)
            continue
        out = out or [[] for _ in chunk]
        for name, recs in zip(chunk, out):
            r = pick(recs or [])
            if not r:
                cache[name] = {"status": "no record"}
            else:
                cache[name] = {
                    "aphia_id": r.get("AphiaID"),
                    "status": r.get("status"),
                    "accepted": r.get("valid_name"),
                    "authority": r.get("authority"),
                }
        if (i // BATCH) % 10 == 0 or i + BATCH >= len(todo):
            CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                             encoding="utf-8")
            print("  %d/%d" % (min(i + BATCH, len(todo)), len(todo)))
        time.sleep(0.35)
    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                     encoding="utf-8")


def report(cache):
    st = Counter(v.get("status") or "?" for v in cache.values())
    total = len(cache)
    print("WoRMS status across %d vault species:" % total)
    for k, n in st.most_common():
        print("   %-28s %5d  (%.2f%%)" % (k, n, 100 * n / total))
    unacc = [(k, v) for k, v in cache.items()
             if v.get("status") not in ("accepted", "no record", None)]
    print("\nnot accepted in WoRMS: %d" % len(unacc))
    for k, v in sorted(unacc)[:15]:
        print("   %-36s %-34s -> %s" % (k, v.get("status"), v.get("accepted")))


def write(cache):
    """Apply cached WoRMS data to every matching note's frontmatter."""
    species = vault_species()
    touched = years = 0
    for name, notes in species.items():
        info = cache.get(name)
        if not info:
            continue
        for note in notes:
            text = V.read_text(note)
            parsed = V.parse_frontmatter(text)
            if not parsed:
                continue
            o, fm, c, body = parsed
            if info.get("aphia_id"):
                fm = V.set_field(fm, "worms_aphia_id", info["aphia_id"])
                fm = V.set_field(fm, "worms_url",
                                 "https://www.marinespecies.org/aphia.php?p=taxdetails&id=%s"
                                 % info["aphia_id"])
            fm = V.set_field(fm, "worms_status", info.get("status") or "no record")
            acc = info.get("accepted")
            if acc and acc != name and info.get("status") not in ("accepted", "no record"):
                fm = V.set_field(fm, "worms_accepted", acc)
            # backfill a missing publication year from the WoRMS authority string
            am = re.search(r'^authorship:[ \t]*"?(.*?)"?$', fm, re.M)
            cur_auth = am.group(1) if am else ""
            w_auth = info.get("authority") or ""
            if cur_auth and not _YEAR.search(cur_auth) and _YEAR.search(w_auth):
                fm = V.set_field(fm, "authorship", w_auth)
                years += 1
            new = o + fm + c + body
            if new != text and V.write_if_changed(note, new):
                touched += 1
    print("Wrote WoRMS fields to %d notes; backfilled %d authorship years." % (touched, years))


def main():
    ap = argparse.ArgumentParser(description="Cross-match vault species against WoRMS.")
    ap.add_argument("--fetch", action="store_true", help="populate the cache from the WoRMS API")
    ap.add_argument("--write", action="store_true", help="apply the cache to note frontmatter")
    ap.add_argument("--report", action="store_true", help="summarise the cache")
    args = ap.parse_args()
    if not (args.fetch or args.write or args.report):
        ap.error("pass --fetch, --write and/or --report")

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    if args.fetch:
        fetch(sorted(vault_species()), cache)
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    if args.report:
        report(cache)
    if args.write:
        write(cache)


if __name__ == "__main__":
    main()
