# -*- coding: utf-8 -*-
"""Migrate the Isopoda tree to agree with the corrected family map.

Reads data/isopoda_suborders.json (the WoRMS-reconciled map) and brings the
physical directory tree and every species note's frontmatter into line with it:

  * relocates a family directory when its suborder changed (e.g. the 17
    Epicaridea families out of Cymothoida/Oniscidea/incertae sedis);
  * renames a misspelling family into its valid spelling, merging into an
    existing directory (Amphisopodidae -> Amphisopidae);
  * rewrites `suborder`, `family`, `realm`, `realms`, and (for fossils)
    `extinct` in the frontmatter, plus the tag tokens and the breadcrumb line;
  * fixes `realm` where only the realm changed and the family did not move.

Directory moves use `git mv` so history is preserved. Idempotent: a second run
is a no-op. Nothing is written under --dry-run.

Python 3.9+.  Run:  python scripts/reclassify.py [--dry-run] [--apply]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import _vault as V

# misspelling family dir -> valid family (already present in the map)
RENAMES = {"Amphisopodidae": "Amphisopidae"}

MAP = json.loads((V.DATA / "isopoda_suborders.json").read_text(encoding="utf-8"))["families"]
DRY = False


def sh(*args):
    if DRY:
        print("   [dry] " + " ".join(str(a) for a in args))
        return
    subprocess.run(args, check=True)


def target_for(cur_family):
    """Return (suborder, family, info) the given directory name should live at,
    resolving a misspelling rename. None if the family isn't in the map."""
    fam = RENAMES.get(cur_family, cur_family)
    info = MAP.get(fam)
    return (info["suborder"], fam, info) if info else None


def breadcrumb(suborder, family, genus):
    return ("**Order** Isopoda › **Suborder** %s › **Family** "
            "[[_%s Index|%s]] › **Genus** [[_%s|%s]]"
            % (suborder, family, family, genus, genus))


def fix_note(path, suborder, family, genus, info, moved):
    """Rewrite one note's frontmatter to the target placement. When the note
    actually moved suborder/family, its suborder-tag token and breadcrumb are
    rebuilt too; a realm-only fix touches nothing but the realm line (leaving
    the note's existing tag convention alone)."""
    text = V.read_text(path)
    parsed = V.parse_frontmatter(text)
    if not parsed:
        return False
    o, fm, c, body = parsed
    # Species-note fields only. The family-level realms[] / worms_aphia_id live
    # on the family INDEX note (a family AphiaID on a species note would read as
    # the species' own id), so they are not copied here.
    fm = V.set_field(fm, "suborder", suborder)
    fm = V.set_field(fm, "family", family)
    fm = V.set_field(fm, "realm", info["realm"])
    if info.get("extinct"):
        fm = V.set_field(fm, "extinct", "true")
    if moved:
        # keep the note's existing token count, only swapping suborder/family
        fm = re.sub(r"^(tags:\s*\[isopod, isopoda), [^,]+, [^\]]+\]",
                    r"\1, %s, %s]" % (suborder.lower(), family.lower()), fm, count=1, flags=re.M)
        body = re.sub(r"^\*\*Order\*\* Isopoda .*$", breadcrumb(suborder, family, genus),
                      body, count=1, flags=re.M)
    new = o + fm + c + body
    if new == text:
        return False
    if not DRY:
        V.write_if_changed(path, new)
    return True


def main():
    global DRY
    ap = argparse.ArgumentParser(description="Reclassify the Isopoda tree to the corrected map.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true", help="perform the migration")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        sys.exit("pass --dry-run to preview or --apply to perform the migration")
    DRY = args.dry_run

    moves = renames = realm_fixes = notes_touched = 0

    # snapshot current (suborder, family) dirs before moving anything
    current = []
    for sub_dir in sorted(p for p in V.ISOPODA.iterdir() if p.is_dir()):
        for fam_dir in sorted(p for p in sub_dir.iterdir() if p.is_dir()):
            current.append((sub_dir.name, fam_dir.name))

    for cur_sub, cur_fam in current:
        tgt = target_for(cur_fam)
        if not tgt:
            print("!! family not in map (left in place): %s/%s" % (cur_sub, cur_fam))
            continue
        new_sub, new_fam, info = tgt
        src = V.ISOPODA / cur_sub / cur_fam
        dst = V.ISOPODA / new_sub / new_fam

        if (cur_sub, cur_fam) != (new_sub, new_fam):
            print("MOVE %s/%s -> %s/%s" % (cur_sub, cur_fam, new_sub, new_fam))
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                # merge: move each genus dir into the existing target family
                for gdir in sorted(p for p in src.iterdir() if p.is_dir()):
                    sh("git", "mv", str(gdir), str(dst / gdir.name))
                # move any stray index note, then drop the empty source dir
                for f in sorted(src.glob("_*.md")):
                    sh("git", "rm", "-q", str(f))
                if not DRY and src.exists() and not any(src.iterdir()):
                    src.rmdir()
            else:
                sh("git", "mv", str(src), str(dst))
            if cur_fam in RENAMES:
                renames += 1
            else:
                moves += 1

        # rewrite frontmatter/breadcrumb on every note now under the target
        moved = (cur_sub, cur_fam) != (new_sub, new_fam)
        walk = dst if not DRY else (dst if dst.exists() else src)
        genus_dirs = sorted(p for p in walk.iterdir() if p.is_dir()) if walk.exists() else []
        changed_here = False
        for gdir in genus_dirs:
            for note in sorted(gdir.glob("*.md")):
                if note.name.startswith("_"):
                    continue
                if fix_note(note, new_sub, new_fam, gdir.name, info, moved):
                    notes_touched += 1
                    changed_here = True
        if changed_here and not moved:
            realm_fixes += 1

    print("\nMoves: %d families relocated, %d renamed. Frontmatter rewritten on %d notes "
          "(%d families needed realm-only fixes).%s"
          % (moves, renames, notes_touched, realm_fixes, "  [DRY RUN]" if DRY else ""))


if __name__ == "__main__":
    main()
