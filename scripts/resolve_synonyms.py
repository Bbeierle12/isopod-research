# -*- coding: utf-8 -*-
"""Resolve the species notes that WoRMS does not accept.

`worms_match.py` records *what* WoRMS says about each species. This script acts
on it. "Resolving" is not one operation — the not-accepted names fall into
classes that need different treatment, and applying a blanket rename would
introduce errors:

  RENAME       the same animal under a new name — a new genus combination
               (Alcirona grandis -> Argathona grandis) or a corrected
               misspelling. The note is moved to the accepted name, into the
               accepted genus/family directory, and the old binomial is kept as
               an Obsidian `aliases` entry so existing links still resolve.

  SYNONYM      the name is a junior synonym of a *different* taxon
               (Androniscus carynthiacus -> Androniscus roseus). The note is not
               renamed — that would duplicate an existing species. It becomes a
               synonym record (`type: synonym`) pointing at the accepted name,
               and stops counting as an accepted species.

  DEMOTED      now a subspecies of another species (Androniscus cavernarum ->
               Androniscus stygius stygius). Treated as a synonym record; the
               vault does not carry subspecies as separate notes.

  SUBSP_REPR   WoRMS additionally carries the *nominotypical* subspecies
               (Alpioniscus absoloni -> Alpioniscus absoloni absoloni). The
               species-level name is valid; renaming would be wrong. Annotated
               only.

  UNPLACEABLE  the accepted placement is "Family incertae sedis <epithet>" — the
               genus has been dissolved and there is no binomial to move to.
               Annotated only.

  FLAG_ONLY    taxon inquirendum / uncertain / nomen nudum with no alternative
               name. Nothing to move; the caveat is already recorded.

Python 3.9+.  Run:  python scripts/resolve_synonyms.py [--dry-run|--apply]
"""
import argparse
import json
import re
import subprocess
import sys

import _vault as V

CACHE = V.DATA / "worms_species.json"
TARGETS = V.DATA / "worms_rename_targets.json"
DRY = False


def sh(*args):
    if DRY:
        return
    subprocess.run(args, check=True)


def classify(name, v):
    """Decide the action for one not-accepted name. Mirrors the doc above."""
    acc = (v.get("accepted") or "").strip()
    st = v.get("status") or ""
    if not acc or acc == name:
        return "FLAG_ONLY"
    if "incertae sedis" in acc:
        return "UNPLACEABLE"
    aw, nw = acc.split(), name.split()
    if len(aw) == 3 and aw[0] == nw[0] and aw[1] == nw[1] and aw[1] == aw[2]:
        return "SUBSP_REPR"
    if len(aw) == 3:
        return "DEMOTED"
    if len(aw) != 2:
        return "UNPLACEABLE"
    if aw[0] == nw[0] and aw[1] != nw[1]:
        return "RENAME" if st.startswith("misspelling") else "SYNONYM"
    if aw[0] != nw[0] and aw[1] == nw[1]:
        return "RENAME"
    return "SYNONYM"


def species_notes():
    out = {}
    for p in V.ISOPODA.rglob("*.md"):
        if p.name.startswith("_"):
            continue
        out[p.stem] = p
    return out


def breadcrumb(sub, fam, gen):
    return ("**Order** Isopoda › **Suborder** %s › **Family** "
            "[[_%s Index|%s]] › **Genus** [[_%s|%s]]" % (sub, fam, fam, gen, gen))


def to_synonym(path, name, accepted, status, linkable=True):
    """Convert a species note into a synonym record pointing at `accepted`.

    The accepted name is wikilinked only when a note for it exists — many
    accepted names are subspecies trinomials or species outside the GBIF-derived
    tree, and linking those would manufacture broken links."""
    text = V.read_text(path)
    parsed = V.parse_frontmatter(text)
    if not parsed:
        return False
    o, fm, c, body = parsed
    fm = V.set_field(fm, "type", "synonym")
    fm = V.set_field(fm, "accepted_name", accepted)
    fm = V.set_field(fm, "worms_status", status)
    fm = V.set_field(fm, "status", "synonym")
    # a synonym is not an accepted species; make that visible in the body too
    target = "[[%s]]" % accepted if linkable else "%s" % accepted
    banner = ("> [!warning] Junior synonym\n"
              "> WoRMS treats **%s** as *%s*. The accepted name is **%s**.\n"
              % (name, status, target))
    body = re.sub(r"^> \[!warning\] Junior synonym\n(?:>.*\n)*", "", body, flags=re.M)
    body = re.sub(r"(^# .*$)", r"\1\n\n" + banner.rstrip(), body, count=1, flags=re.M)
    return V.write_if_changed(path, o + fm + c + body) if not DRY else True


def annotate(path, note, accepted, status):
    """Record a taxonomic caveat without moving or reclassifying the note."""
    text = V.read_text(path)
    parsed = V.parse_frontmatter(text)
    if not parsed:
        return False
    o, fm, c, body = parsed
    fm = V.set_field(fm, "worms_note", note)
    if accepted and accepted != path.stem:
        fm = V.set_field(fm, "worms_accepted", accepted)
    return V.write_if_changed(path, o + fm + c + body) if not DRY else True


def rename(path, old, new, tinfo, fammap):
    """Move a note to its accepted binomial, into the accepted genus/family."""
    new_gen = new.split()[0]
    new_fam = tinfo.get("family") or path.parent.parent.name
    finfo = fammap.get(new_fam)
    if not finfo:                      # unknown family -> keep the current tree position
        new_fam = path.parent.parent.name
        finfo = fammap.get(new_fam, {})
    sub = finfo.get("suborder", path.parent.parent.parent.name)
    realm = finfo.get("realm")
    dst = V.ISOPODA / V.safe(sub) / V.safe(new_fam) / V.safe(new_gen) / (V.safe(new) + ".md")
    if dst.exists():
        return False, "target exists"

    text = V.read_text(path)
    parsed = V.parse_frontmatter(text)
    if not parsed:
        return False, "no frontmatter"
    o, fm, c, body = parsed
    fm = V.set_field(fm, "scientificName", new)
    fm = V.set_field(fm, "genus", new_gen)
    fm = V.set_field(fm, "family", new_fam)
    fm = V.set_field(fm, "suborder", sub)
    if realm:
        fm = V.set_field(fm, "realm", realm)
    if tinfo.get("aphia_id"):
        fm = V.set_field(fm, "worms_aphia_id", tinfo["aphia_id"])
        fm = V.set_field(fm, "worms_url",
                         "https://www.marinespecies.org/aphia.php?p=taxdetails&id=%s" % tinfo["aphia_id"])
    fm = V.set_field(fm, "worms_status", tinfo.get("status") or "accepted")
    if tinfo.get("authority"):
        fm = V.set_field(fm, "authorship", tinfo["authority"])
    fm = V.set_field(fm, "former_name", old)
    # keep the superseded binomial resolvable in Obsidian — a real YAML list, so
    # pass a Python list and let emit_val render the flow sequence unquoted
    fm = V.set_field(fm, "aliases", [old])
    fm = re.sub(r"^worms_accepted:.*\n", "", fm, flags=re.M)
    fm = re.sub(r"^tags:.*$", "tags: [isopod, isopoda, %s, %s]" % (sub.lower(), new_fam.lower()),
                fm, count=1, flags=re.M)
    body = re.sub(r"^# .*$", "# %s" % new, body, count=1, flags=re.M)
    body = re.sub(r"^\*\*(?:Order|Suborder)\*\* .*$", breadcrumb(sub, new_fam, new_gen),
                  body, count=1, flags=re.M)
    if "_Formerly_" not in body:
        body = re.sub(r"(^\*\*Order\*\* .*$)", r"\1\n\n_Formerly_ **%s** _(superseded name)._" % old,
                      body, count=1, flags=re.M)

    if DRY:
        print("   [dry] %s -> %s" % (path.relative_to(V.ISOPODA), dst.relative_to(V.ISOPODA)))
        return True, "ok"
    dst.parent.mkdir(parents=True, exist_ok=True)
    sh("git", "mv", str(path), str(dst))
    V.write_if_changed(dst, o + fm + c + body)
    return True, "ok"


def main():
    global DRY
    ap = argparse.ArgumentParser(description="Resolve WoRMS-unaccepted species notes.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        sys.exit("pass --dry-run or --apply")
    DRY = args.dry_run

    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    targets = json.loads(TARGETS.read_text(encoding="utf-8")) if TARGETS.exists() else {}
    fammap = json.loads((V.DATA / "isopoda_suborders.json").read_text(encoding="utf-8"))["families"]
    notes = species_notes()

    counts = {k: 0 for k in ("RENAME", "SYNONYM", "DEMOTED", "SUBSP_REPR", "UNPLACEABLE", "FLAG_ONLY", "MERGED")}
    for name, v in sorted(cache.items()):
        if v.get("status") in ("accepted", "no record", None):
            continue
        path = notes.get(name)
        if not path:
            continue
        cls = classify(name, v)
        acc = (v.get("accepted") or "").strip()
        st = v.get("status")

        if cls == "RENAME":
            if acc in notes:            # accepted name already present -> merge, don't rename
                if to_synonym(path, name, acc, st, acc in notes):
                    counts["MERGED"] += 1
                continue
            ok, why = rename(path, name, acc, targets.get(acc, {}), fammap)
            if ok:
                counts["RENAME"] += 1
            elif to_synonym(path, name, acc, st, acc in notes):
                counts["MERGED"] += 1
        elif cls in ("SYNONYM", "DEMOTED"):
            if to_synonym(path, name, acc, st, acc in notes):
                counts[cls] += 1
        elif cls == "SUBSP_REPR":
            if annotate(path, "species-level name is valid; WoRMS also carries the "
                              "nominotypical subspecies %s" % acc, None, st):
                counts[cls] += 1
        elif cls == "UNPLACEABLE":
            if annotate(path, "genus placement unresolved in WoRMS (%s)" % acc, None, st):
                counts[cls] += 1
        else:
            if annotate(path, "WoRMS caveat: %s" % st, None, st):
                counts[cls] += 1

    print("\n".join("%-12s %4d" % (k, counts[k]) for k in
                    ("RENAME", "MERGED", "SYNONYM", "DEMOTED", "SUBSP_REPR", "UNPLACEABLE", "FLAG_ONLY"))
          + ("\n[DRY RUN]" if DRY else ""))


if __name__ == "__main__":
    main()
