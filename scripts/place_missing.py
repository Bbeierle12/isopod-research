# -*- coding: utf-8 -*-
"""File the GBIF-accepted species the family-first crawl could not reach.

`taxonomy.py` enumerates species via GBIF and files them under
suborder/family/genus. 49 accepted Isopoda species carry **no family** in the
GBIF backbone, so a family-keyed tree has nowhere to put them; a further 10 were
simply absent. This script closes that gap from `data/unplaced_species.json`,
whose placements were resolved as follows:

  * family from WoRMS when it names a real one (Philosciidae, Hekelidae, …);
  * otherwise WoRMS's superfamily-level placement, kept as an explicit
    placeholder family (`Janiroidea incertae sedis`, `Cryptoniscoidea incertae
    sedis`, …) whose suborder was verified through AphiaClassification;
  * otherwise GBIF's family;
  * otherwise `Isopoda incertae sedis` with `realm: unknown` — undetermined
    rather than guessed.

Fossil status is taken from PaleoBioDB (7 of the 12 otherwise-unplaceable names
are confirmed extinct, with an age range); the rest carry no extinct flag
because no source confirms one.

Placeholder families are registered in `data/isopoda_suborders.json` with
`placeholder: true` so the tree stays consistent with the family map without
implying they are real taxa.

Python 3.9+.  Run:  python scripts/place_missing.py [--dry-run|--apply]
"""
import argparse
import json
import sys

import _vault as V
import taxonomy as T

DATA = V.DATA / "unplaced_species.json"
MAP = V.DATA / "isopoda_suborders.json"

# realm carried by each placeholder family (verified suborder -> realm)
PLACEHOLDER_REALM = {
    "Oniscidea incertae sedis": "terrestrial",
    "Janiroidea incertae sedis": "marine",
    "Cryptoniscoidea incertae sedis": "marine",
    "Phreatoicidea incertae sedis": "freshwater",
    "Isopoda incertae sedis": "unknown",
}


def register_placeholders(species, dry):
    """Add any placeholder family used by these species to the family map."""
    doc = json.loads(MAP.read_text(encoding="utf-8"))
    fams = doc["families"]
    added = []
    for rec in species.values():
        fam = rec["family"]
        if fam in fams or fam not in PLACEHOLDER_REALM:
            continue
        realm = PLACEHOLDER_REALM[fam]
        fams[fam] = {"suborder": rec["suborder"], "realm": realm, "realms": [realm],
                     "placeholder": True,
                     "note": "not a real family — holds species whose family-level "
                             "placement is unresolved in both GBIF and WoRMS"}
        added.append(fam)
    if added and not dry:
        doc["families"] = dict(sorted(fams.items()))
        MAP.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added


def note_text(name, rec):
    """Render via taxonomy.py's template, then add the provenance fields."""
    genus = name.split()[0]
    text = T.render_note(name, rec.get("authorship") or "", genus, rec["family"],
                         rec["suborder"], rec["realm"], rec.get("gbif_id"))
    o, fm, c, body = V.parse_frontmatter(text)
    for key in ("worms_aphia_id", "worms_accepted", "pbdb_id", "pbdb_age_ma"):
        if rec.get(key):
            fm = V.set_field(fm, key, rec[key])
    # every species states a WoRMS verdict; absence from the register is itself
    # a verdict ("no record"), matching what worms_match.py writes
    fm = V.set_field(fm, "worms_status", rec.get("worms_status") or "no record")
    if rec.get("worms_aphia_id"):
        fm = V.set_field(fm, "worms_url",
                         "https://www.marinespecies.org/aphia.php?p=taxdetails&id=%s"
                         % rec["worms_aphia_id"])
    if rec.get("extinct"):
        fm = V.set_field(fm, "extinct", True)   # real YAML boolean, not the string "true"
    if rec["family"].endswith("incertae sedis"):
        fm = V.set_field(fm, "worms_note",
                         "family-level placement unresolved; filed under %s" % rec["family"])
    return o + fm + c + body


def main():
    ap = argparse.ArgumentParser(description="File GBIF species the crawl could not reach.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        sys.exit("pass --dry-run or --apply")
    dry = args.dry_run

    species = json.loads(DATA.read_text(encoding="utf-8"))["species"]
    added = register_placeholders(species, dry)
    if added:
        print("placeholder families registered: %s" % ", ".join(sorted(added)))

    wrote = existed = 0
    for name, rec in sorted(species.items()):
        genus = name.split()[0]
        path = (V.ISOPODA / V.safe(rec["suborder"]) / V.safe(rec["family"])
                / V.safe(genus) / (V.safe(name) + ".md"))
        if path.exists():
            existed += 1
            continue
        if dry:
            print("   [dry] %s" % path.relative_to(V.ISOPODA))
            wrote += 1
            continue
        if V.write_if_changed(path, note_text(name, rec)):
            wrote += 1
    print("Filed %d species (%d already present).%s" % (wrote, existed, "  [DRY RUN]" if dry else ""))


if __name__ == "__main__":
    main()
