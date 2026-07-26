# -*- coding: utf-8 -*-
"""Assert every structural invariant of the vault. Read-only and offline.

This is the regression net for the pipeline. Each fix in the vault's history was
verified once by hand; this turns those one-off checks into something CI can
enforce. It exercises no network and writes no files, so it is safe to run
anywhere, including on a pull request.

Run:  python scripts/verify.py [--quiet]
Exit: 0 if every check passes, 1 otherwise.
"""
import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

import _vault as V

try:
    import yaml
except ImportError:                                    # pragma: no cover
    sys.exit("verify.py needs PyYAML:  pip install pyyaml")

CHECKS = []
MAX_SHOWN = 8
OPEN_NOM = ("sp.", "spp.", "cf.", "aff.", "var.", "nr.")
# "unknown" is a deliberate member: a handful of species (mostly fossils) have no
# determined environment in GBIF, WoRMS or PaleoBioDB, and recording that beats
# guessing one.
REALMS = {"terrestrial", "littoral", "brackish", "freshwater", "interstitial",
          "marine", "unknown"}


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


# ---------------------------------------------------------------- helpers
def _species_notes():
    """(path, frontmatter_dict_raw, body) for every accepted-species note."""
    for p in V.species_note_paths():
        parsed = V.parse_frontmatter(V.read_text(p))
        if parsed:
            yield p, parsed[1], parsed[3]


def _fm_get(fm, key):
    m = re.search(r"^%s:[ \t]*(.*)$" % re.escape(key), fm, re.M)
    return m.group(1).strip().strip('"') if m else ""


# ---------------------------------------------------------------- checks
@check("every script compiles")
def _():
    bad = []
    for p in sorted(Path(__file__).parent.glob("*.py")):
        r = subprocess.run([sys.executable, "-m", "py_compile", str(p)],
                           capture_output=True, text=True)
        if r.returncode:
            bad.append("%s: %s" % (p.name, r.stderr.strip().splitlines()[-1]))
    return bad


@check("all frontmatter is valid YAML")
def _():
    bad = []
    for p in V.ISOPODA.rglob("*.md"):
        parsed = V.parse_frontmatter(V.read_text(p))
        if not parsed:
            continue
        try:
            yaml.safe_load(parsed[1])
        except Exception as e:
            bad.append("%s: %s" % (p.name, str(e).splitlines()[0]))
    return bad


@check("species frontmatter matches its directory path")
def _():
    bad = []
    for p, fm, _b in _species_notes():
        parts = p.relative_to(V.ISOPODA).parts
        if len(parts) != 4:
            bad.append("%s: unexpected depth %d" % (p.name, len(parts)))
            continue
        want = (parts[0], parts[1], parts[2], parts[3][:-3])
        got = (_fm_get(fm, "suborder"), _fm_get(fm, "family"),
               _fm_get(fm, "genus"), _fm_get(fm, "scientificName"))
        if want != got:
            bad.append("%s: path%s != frontmatter%s" % (p.name, want, got))
    return bad


def _is_content(p):
    """Vault content, as opposed to prose about the vault. `docs/` holds design
    plans and reviews whose examples contain literal placeholder links
    (`[[_<Family> Index]]`, `[[Genus species]]`); Welcome.md is Obsidian's
    boilerplate. Neither should be able to fail a link check."""
    parts = p.relative_to(V.VAULT).parts
    return parts[0] not in ("docs", ".obsidian", ".git") and p.name != "Welcome.md"


_FENCE = re.compile(r"^```.*?^```", re.M | re.S)


@check("no broken wikilinks")
def _():
    present = {p.stem for p in V.VAULT.rglob("*.md") if ".git" not in p.parts}
    # Obsidian aliases also resolve a link
    for p in V.ISOPODA.rglob("*.md"):
        parsed = V.parse_frontmatter(V.read_text(p))
        if not parsed:
            continue
        m = re.search(r"^aliases:[ \t]*\[(.*)\]", parsed[1], re.M)
        if m:
            present.update(a.strip() for a in m.group(1).split(",") if a.strip())
    missing = collections.Counter()
    for p in V.VAULT.rglob("*.md"):
        if ".git" in p.parts or not _is_content(p):
            continue
        body = _FENCE.sub("", V.read_text(p) or "")   # code samples aren't links
        for tgt in re.findall(r"\[\[([^\]|#]+)", body):
            tgt = tgt.strip().replace("\\", "")
            if tgt and tgt not in present:
                missing[tgt] += 1
    return ["%s (x%d)" % (k, n) for k, n in missing.most_common()]


@check("binomials are ICZN-formatted (Genus capitalised, epithet lowercase)")
def _():
    ok = re.compile(r"^[A-Z][a-z]+ [a-z][a-z-]+( [a-z][a-z-]+)?$")
    return ["%s: %r" % (p.name, _fm_get(fm, "scientificName"))
            for p, fm, _b in _species_notes()
            if not ok.match(_fm_get(fm, "scientificName"))]


@check("no open nomenclature in any species/epithet field")
def _():
    bad = []
    for p, fm, _b in _species_notes():
        sci = _fm_get(fm, "scientificName")
        if any(t in sci.split() for t in OPEN_NOM):
            bad.append("note %s: %r" % (p.name, sci))
    recs = json.loads((V.DATA / "isopods.json").read_text(encoding="utf-8"))["records"]
    for r in recs:
        if str(r.get("species", "")).strip() in OPEN_NOM:
            bad.append("isopods.json %s: species=%r" % (r.get("id"), r["species"]))
    csv_path = V.DATA / "isopods.csv"
    if csv_path.exists():
        import csv as _csv
        with open(csv_path, encoding="utf-8", newline="") as f:
            for row in _csv.DictReader(f):
                if (row.get("species") or "").strip() in OPEN_NOM:
                    bad.append("isopods.csv %s: species=%r" % (row.get("id"), row["species"]))
    return bad


@check("no duplicate binomials among accepted species")
def _():
    seen = collections.defaultdict(list)
    for p, fm, _b in _species_notes():
        seen[_fm_get(fm, "scientificName")].append(p.name)
    return ["%s appears %dx" % (k, len(v)) for k, v in seen.items() if len(v) > 1]


@check("every species records both authorities (gbif_id + worms_status)")
def _():
    bad = []
    for p, fm, _b in _species_notes():
        if not _fm_get(fm, "gbif_id"):
            bad.append("%s: no gbif_id" % p.name)
        if not _fm_get(fm, "worms_status"):
            bad.append("%s: no worms_status" % p.name)
    return bad


@check("realm values are from the controlled vocabulary")
def _():
    return ["%s: realm=%r" % (p.name, _fm_get(fm, "realm"))
            for p, fm, _b in _species_notes()
            if _fm_get(fm, "realm") not in REALMS]


@check("every family on disk is in the family map")
def _():
    fams = json.loads((V.DATA / "isopoda_suborders.json").read_text(encoding="utf-8"))["families"]
    bad = []
    for sub in sorted(p for p in V.ISOPODA.iterdir() if p.is_dir()):
        for fam in sorted(p for p in sub.iterdir() if p.is_dir()):
            info = fams.get(fam.name)
            if not info:
                bad.append("%s/%s absent from isopoda_suborders.json" % (sub.name, fam.name))
            elif info["suborder"] != sub.name:
                bad.append("%s/%s: map says suborder %s" % (sub.name, fam.name, info["suborder"]))
    return bad


@check("synonym records name their accepted taxon")
def _():
    bad = []
    for p in V.ISOPODA.rglob("*.md"):
        if p.name.startswith("_") or not V.is_synonym_note(p):
            continue
        fm = V.parse_frontmatter(V.read_text(p))[1]
        if not _fm_get(fm, "accepted_name"):
            bad.append("%s: type synonym but no accepted_name" % p.name)
    return bad


@check("ecology source_refs all resolve to a reference")
def _():
    doc = json.loads((V.DATA / "ecology.json").read_text(encoding="utf-8"))
    refs = doc.get("references", {})
    bad = []
    for e in doc["entries"]:
        for k in (e.get("source_refs") or []):
            if k not in refs:
                bad.append("%s cites unknown ref %r" % (e["match"], k))
        if not (e.get("source_refs") or e.get("source_note")):
            bad.append("%s has neither a source nor a source_note" % e["match"])
    for k, r in refs.items():
        if not r.get("citation") or not r.get("verified"):
            bad.append("reference %s incomplete" % k)
    return bad


@check("family-level ecology is cited, and never overrides species-level data")
def _():
    doc = json.loads((V.DATA / "ecology.json").read_text(encoding="utf-8"))
    refs = doc.get("references", {})
    fam = doc.get("family_ecology", {})
    species_level = {e["match"] for e in doc["entries"] if not e["match"].endswith(" *")}
    fams_on_disk = {p.name for sub in V.ISOPODA.iterdir() if sub.is_dir()
                    for p in sub.iterdir() if p.is_dir()}
    bad = []
    for name, fe in fam.items():
        if name not in fams_on_disk:
            bad.append("family_ecology names %r, which is not a family on disk" % name)
        if not fe.get("source_refs"):
            bad.append("%s: family-level assignment with no citation" % name)
        for k in fe.get("source_refs") or []:
            if k not in refs:
                bad.append("%s cites unknown ref %r" % (name, k))
        if fe.get("evd") != "b":
            bad.append("%s: family-level inference must be grade b, got %r" % (name, fe.get("evd")))
    # a species with its own entry must keep species-level evidence, not "(family)"
    for p, fm, _b in _species_notes():
        sci = _fm_get(fm, "scientificName")
        if sci in species_level and "(family)" in _fm_get(fm, "ecology_evidence"):
            bad.append("%s has a species-level entry but carries family-level evidence" % sci)
    return bad


@check("index notes are up to date with the tree")
def _():
    """Regenerate index content in memory and compare — catches a tree edited
    without re-running isopoda_index.py. Writes nothing."""
    import isopoda_index as IX
    tree = IX.scan_tree()
    bad = []
    for suborder in sorted(tree):
        families = tree[suborder]
        sub_dir = V.ISOPODA / suborder
        for fam_name in sorted(families):
            fam_dir = sub_dir / fam_name
            gs = {}
            for gen_name in sorted(families[fam_name]["genera"]):
                gen_dir = fam_dir / gen_name
                n = sum(1 for f in gen_dir.iterdir()
                        if f.suffix == ".md" and not f.name.startswith("_")
                        and not V.is_synonym_note(f))
                gs[gen_name] = n
                want = IX.genus_note(gen_name, fam_name, suborder, n)
                if V.read_text(gen_dir / ("_%s.md" % gen_name)) != want:
                    bad.append("stale genus index: %s/%s/%s" % (suborder, fam_name, gen_name))
            want = IX.family_note(fam_name, suborder, gs, families[fam_name]["realm"])
            if V.read_text(fam_dir / ("_%s Index.md" % fam_name)) != want:
                bad.append("stale family index: %s/%s" % (suborder, fam_name))
        want = IX.suborder_note(suborder, families, IX.suborder_realm(suborder, families))
        if V.read_text(sub_dir / ("_%s Index.md" % suborder)) != want:
            bad.append("stale suborder index: %s" % suborder)
    return bad


@check("the database loads with no constraint violations")
def _():
    r = subprocess.run([sys.executable, str(Path(__file__).parent / "build_db.py")],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return []
    tail = [l for l in r.stdout.splitlines() if "violation" in l.lower() or "CHECK" in l]
    return tail or [(r.stderr or r.stdout).strip().splitlines()[-1]]


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Verify the vault's structural invariants.")
    ap.add_argument("--quiet", action="store_true", help="only print failures")
    args = ap.parse_args()

    failed = 0
    for name, fn in CHECKS:
        try:
            problems = fn() or []
        except Exception as e:                      # a crashing check is a failure
            problems = ["check raised %s: %s" % (type(e).__name__, e)]
        if problems:
            failed += 1
            print("FAIL  %s  (%d)" % (name, len(problems)))
            for p in problems[:MAX_SHOWN]:
                print("        %s" % p)
            if len(problems) > MAX_SHOWN:
                print("        ... and %d more" % (len(problems) - MAX_SHOWN))
        elif not args.quiet:
            print("ok    %s" % name)

    print("\n%d/%d checks passed." % (len(CHECKS) - failed, len(CHECKS)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
