# -*- coding: utf-8 -*-
"""Crawl GBIF for the whole Isopoda order and scaffold one Markdown note per
accepted species, filed suborder -> family -> genus -> species.

Enumeration uses the GBIF *search* endpoint (`/species/search`), which returns
every accepted species in the order — with its family and genus already on each
record — in ~12 paged requests, instead of the old design's ~1,138 per-genus
`/children` calls. This also surfaces species that carry no family in the
backbone (unreachable by a family-first descent); they are reported, not
silently dropped.

Idempotent: an existing note is never overwritten (hand edits and enrichment
survive). Pass --refresh to re-render the managed frontmatter of existing notes.

Python 3.9+.  Run:  python scripts/taxonomy.py [--refresh] [--limit-family NAME]
"""
import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

import _vault as V

if sys.version_info < (3, 9):
    sys.exit("taxonomy.py requires Python 3.9+")

GBIF = "https://api.gbif.org/v1"
BACKBONE = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"   # GBIF Backbone Taxonomy
ISOPODA_KEY = 643
UA = "isopod-research/1.0 (+https://github.com/bbeierle12/isopod-research)"
LOG = V.VAULT / "logs" / "taxonomy.log"


class FetchError(RuntimeError):
    """Raised when a URL cannot be retrieved after exhausting retries, or on a
    permanent (4xx, non-429) HTTP status."""


def get_json(url, attempts=5):
    """GET and parse JSON with exponential backoff + jitter. Retries only on
    transient failures (5xx, 429, network, decode); raises FetchError on a
    permanent 4xx or after the last attempt — never returns a partial/sentinel
    that the caller could mistake for 'no more data'."""
    for a in range(attempts):
        wait = None
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                wait = float(e.headers.get("Retry-After") or 0) or (2 ** a)
            else:
                raise FetchError("HTTP %d for %s" % (e.code, url)) from e
        except (urllib.error.URLError, TimeoutError, ValueError):
            wait = 2 ** a
        if a == attempts - 1:
            raise FetchError("gave up after %d attempts: %s" % (attempts, url))
        time.sleep(wait + random.uniform(0, 0.5))


def fetch_accepted_species():
    """Return every accepted Isopoda species in the backbone, as GBIF search
    records (each carries key/canonicalName/family/genus/authorship)."""
    out = []
    offset = 0
    while True:
        url = "%s/species/search?%s" % (GBIF, urllib.parse.urlencode({
            "datasetKey": BACKBONE, "higherTaxonKey": ISOPODA_KEY,
            "rank": "SPECIES", "status": "ACCEPTED",
            "limit": 1000, "offset": offset,
        }))
        data = get_json(url)
        out.extend(data.get("results", []))
        if data.get("endOfRecords") or not data.get("results"):
            break
        offset += 1000
        time.sleep(0.2)
    return out


def note_body(sp_name, auth, suborder, fam_name, gen_name, gbif_id):
    # Breadcrumb link targets match the index notes isopoda_index.py generates:
    # family -> "_<Family> Index", genus -> "_<Genus>".
    return (
        "\n# %s %s\n\n"
        "**Order** Isopoda › **Suborder** %s › **Family** "
        "[[_%s Index|%s]] › **Genus** [[_%s|%s]]\n\n"
        "## Overview\n\n\n## Distribution & habitat\n\n\n"
        "## References\n- GBIF: https://www.gbif.org/species/%s\n"
    ) % (sp_name, auth, suborder, fam_name, fam_name, gen_name, gen_name, gbif_id)


def render_note(sp_name, auth, gen_name, fam_name, suborder, realm, gbif_id):
    """Full note text. Authorship is emitted via json.dumps so a value with a
    quote or backslash yields valid YAML (the old inline f-string could not)."""
    fm = "\n".join([
        "---",
        "type: species",
        "scientificName: %s" % sp_name,
        "authorship: %s" % json.dumps(auth or ""),
        "genus: %s" % gen_name,
        "family: %s" % fam_name,
        "suborder: %s" % suborder,
        "realm: %s" % realm,
        "gbif_id: %s" % gbif_id,
        "gbif_url: https://www.gbif.org/species/%s" % gbif_id,
        "common_name:", "distribution:", "habitat:", "ecomorph:",
        "conglobation_type:", "terrestrialization:", "habitat_stratum:",
        "trophic_guild:", "reproduction_mode:", "ecology_evidence:", "sources:",
        "status: stub",
        "tags: [isopod, isopoda, %s, %s]" % (suborder.lower(), fam_name.lower()),
        "---",
    ])
    return fm + note_body(sp_name, auth, suborder, fam_name, gen_name, gbif_id)


def log(line, echo=True):
    if echo:
        print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser(description="Crawl GBIF Isopoda into the vault.")
    ap.add_argument("--refresh", action="store_true",
                    help="re-render managed frontmatter of existing notes")
    ap.add_argument("--limit-family", metavar="NAME",
                    help="only process this family (dry-run aid)")
    args = ap.parse_args()

    smap = json.loads((V.DATA / "isopoda_suborders.json").read_text(encoding="utf-8"))["families"]

    log("Fetching accepted Isopoda species from GBIF search endpoint...")
    species = fetch_accepted_species()
    log("GBIF returned %d accepted species." % len(species))

    by_family = defaultdict(list)
    unplaced = []
    for sp in species:
        fam = sp.get("family")
        (by_family[fam] if fam else unplaced).append(sp)

    written = skipped_existing = 0
    skipped_family = defaultdict(int)
    for fam_name, rows in sorted(by_family.items()):
        if args.limit_family and fam_name != args.limit_family:
            continue
        info = smap.get(fam_name)
        if not info:
            skipped_family[fam_name] = len(rows)
            continue
        suborder = info["suborder"]
        if suborder == "Oniscidea":                 # built by the generate.py pipeline
            continue
        realm = info["realm"]
        fam_written = 0
        for sp in rows:
            name = sp.get("canonicalName") or sp.get("species")
            gen_name = sp.get("genus")
            if not name or not gen_name:
                continue
            gbif_id = sp.get("key")
            auth = sp.get("authorship", "") or ""
            path = V.ISOPODA / V.safe(suborder) / V.safe(fam_name) / V.safe(gen_name) / (V.safe(name) + ".md")
            text = render_note(name, auth, gen_name, fam_name, suborder, realm, gbif_id)
            if path.exists() and not args.refresh:
                skipped_existing += 1
                continue
            if V.write_if_changed(path, text):
                written += 1
                fam_written += 1
        log("[%s] %s species=%d written=%d" % (suborder, fam_name, len(rows), fam_written))

    log("Done. wrote/updated=%d, left-existing=%d." % (written, skipped_existing))
    if unplaced:
        log("UNPLACED (no family in backbone, not filed): %d species -- %s"
            % (len(unplaced), ", ".join(sorted({s.get("genus") or "?" for s in unplaced}))))
    if skipped_family:
        log("SKIPPED (family absent from data/isopoda_suborders.json): %s"
            % dict(sorted(skipped_family.items())))


if __name__ == "__main__":
    main()
