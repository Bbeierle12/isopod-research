# -*- coding: utf-8 -*-
"""Generate the hierarchical index notes for the Isopoda tree:

    _Isopoda Index.md                      (order)
    <Suborder>/_<Suborder> Index.md        (per suborder)
    <Suborder>/<Family>/_<Family> Index.md (per family)   <- NEW
    <Suborder>/<Family>/<Genus>/_<Genus>.md (per genus)   <- NEW

The family- and genus-level notes are what every species-note breadcrumb links
to (`[[_<Family> Index|...]]`, `[[_<Genus>|...]]`); before this script emitted
them, all ~14.5k of those links were dead.

Counts are taken from what is actually on disk, not from the family map, so a
family with no species notes is not reported as if it had a directory. Writes
are idempotent (skipped when unchanged); the `generated:` stamp is written only
when the note's content otherwise changed, so re-running on an unchanged tree is
a no-op.

Python 3.9+.  Run:  python scripts/isopoda_index.py
"""
import json
from collections import defaultdict

import _vault as V

# The generated date is derived from the family map's source stamp, not the wall
# clock, so a no-op run doesn't churn every note with a new date.
_SRC = json.loads((V.DATA / "isopoda_suborders.json").read_text(encoding="utf-8"))
FAMILY_MAP = _SRC["families"]
GENERATED = _SRC.get("_generated", "GBIF Backbone Taxonomy")


def realm_label(info):
    """A family/suborder may span several realms; show them all rather than an
    arbitrary first one."""
    realms = info.get("realms") or [info["realm"]]
    return ", ".join(realms)


def scan_tree():
    """Walk the on-disk tree and return
    {suborder: {family: {"genera": set, "species": int, "realm": str}}}."""
    tree = defaultdict(lambda: defaultdict(lambda: {"genera": set(), "species": 0, "realm": ""}))
    if not V.ISOPODA.exists():
        return tree
    for sub_dir in sorted(p for p in V.ISOPODA.iterdir() if p.is_dir()):
        for fam_dir in sorted(p for p in sub_dir.iterdir() if p.is_dir()):
            info = FAMILY_MAP.get(fam_dir.name, {})
            fam = tree[sub_dir.name][fam_dir.name]
            fam["realm"] = realm_label(info) if info else ""
            for gen_dir in sorted(p for p in fam_dir.iterdir() if p.is_dir()):
                fam["genera"].add(gen_dir.name)
                n = sum(1 for f in gen_dir.iterdir()
                        if f.suffix == ".md" and not f.name.startswith("_"))
                fam["species"] += n
    return tree


def genus_note(genus, family, suborder, species_count):
    return "\n".join([
        "---", "type: genus", "genus: %s" % genus, "family: %s" % family,
        "suborder: %s" % suborder, "species_count: %d" % species_count,
        "source: GBIF Backbone Taxonomy (api.gbif.org)",
        "tags: [isopod, %s, genus-index]" % suborder.lower(), "---", "",
        "# %s (Genus)" % genus, "",
        "**Family** [[_%s Index|%s]] · **Suborder** %s · %d accepted species."
        % (family, family, suborder, species_count), "",
    ]) + "\n"


def family_note(family, suborder, genera_species, realm):
    genera = sorted(genera_species)
    gtot = len(genera)
    stot = sum(genera_species.values())
    lines = [
        "---", "type: index", "group: %s" % family, "suborder: %s" % suborder,
        "genus_count: %d" % gtot, "species_count: %d" % stot,
        "realm: %s" % realm, "source: GBIF Backbone Taxonomy (api.gbif.org)",
        "tags: [isopod, %s, family-index]" % suborder.lower(), "---", "",
        "# %s (Family)" % family, "",
        "Suborder %s · %d genera · %d accepted species." % (suborder, gtot, stot), "",
        "## Genera", "", "| Genus | Species |", "|---|---:|",
    ]
    for g in genera:
        lines.append("| [[_%s|%s]] | %d |" % (g, g, genera_species[g]))
    lines.append("| **TOTAL** | **%d** |" % stot)
    lines.append("")
    return "\n".join(lines) + "\n"


def suborder_note(suborder, families, realm):
    fam_names = sorted(families)
    gtot = sum(len(families[f]["genera"]) for f in fam_names)
    stot = sum(families[f]["species"] for f in fam_names)
    lines = [
        "---", "type: index", "group: %s" % suborder,
        "family_count: %d" % len(fam_names), "genus_count: %d" % gtot,
        "species_count: %d" % stot, "realm: %s" % realm,
        "source: GBIF Backbone Taxonomy (api.gbif.org)",
        "tags: [isopod, %s, master-index]" % suborder.lower(), "---", "",
        "# %s (Suborder)" % suborder, "",
        "This vault section covers **%d families, %d genera, and %d accepted species**. Realm: %s"
        % (len(fam_names), gtot, stot, realm), "",
        "## Families", "", "| Family | Genera | Species |", "|---|---:|---:|",
    ]
    for f in fam_names:
        lines.append("| [[_%s Index\\|%s]] | %d | %d |"
                     % (f, f, len(families[f]["genera"]), families[f]["species"]))
    lines.append("| **TOTAL** | **%d** | **%d** |" % (gtot, stot))
    lines.append("")
    return "\n".join(lines) + "\n"


def suborder_realm(suborder, families):
    """Realm of a suborder = the union across its families (deduped, ordered)."""
    seen, out = set(), []
    for f in sorted(families):
        info = FAMILY_MAP.get(f, {})
        for r in (info.get("realms") or ([info["realm"]] if info.get("realm") else [])):
            if r not in seen:
                seen.add(r)
                out.append(r)
    return ", ".join(out) or "unknown"


def main():
    tree = scan_tree()
    wrote = 0
    sub_rows = []
    tot_fam = tot_gen = tot_sp = 0

    for suborder in sorted(tree):
        families = tree[suborder]
        realm = suborder_realm(suborder, families)
        sub_dir = V.ISOPODA / suborder

        for fam_name in sorted(families):
            fam = families[fam_name]
            genera_species = {}
            fam_dir = sub_dir / fam_name
            for gen_name in sorted(fam["genera"]):
                gen_dir = fam_dir / gen_name
                n = sum(1 for f in gen_dir.iterdir()
                        if f.suffix == ".md" and not f.name.startswith("_"))
                genera_species[gen_name] = n
                wrote += V.write_if_changed(
                    gen_dir / ("_%s.md" % gen_name),
                    genus_note(gen_name, fam_name, suborder, n))
            wrote += V.write_if_changed(
                fam_dir / ("_%s Index.md" % fam_name),
                family_note(fam_name, suborder, genera_species, fam["realm"]))

        gtot = sum(len(f["genera"]) for f in families.values())
        stot = sum(f["species"] for f in families.values())
        tot_fam += len(families)
        tot_gen += gtot
        tot_sp += stot
        wrote += V.write_if_changed(
            sub_dir / ("_%s Index.md" % suborder),
            suborder_note(suborder, families, realm))
        sub_rows.append("| [[_%s Index\\|%s]] | %s | %d | %d | %d |"
                        % (suborder, suborder, realm, len(families), gtot, stot))

    master = "\n".join([
        "---", "type: index", "group: Isopoda",
        "suborder_count: %d" % len(tree), "family_count: %d" % tot_fam,
        "genus_count: %d" % tot_gen, "species_count: %d" % tot_sp,
        "source: GBIF Backbone Taxonomy (api.gbif.org)",
        "tags: [isopod, isopoda, master-index]", "---", "",
        "# Isopoda (Order)", "",
        "The order Isopoda. This vault section covers **%d suborders, %d families, "
        "%d genera, and %d accepted species**." % (len(tree), tot_fam, tot_gen, tot_sp), "",
        "## Suborders", "", "| Suborder | Realm | Families | Genera | Species |",
        "|---|---|---:|---:|---:|",
        "\n".join(sub_rows),
        "| **TOTAL** | | **%d** | **%d** | **%d** |" % (tot_fam, tot_gen, tot_sp), "",
    ]) + "\n"
    wrote += V.write_if_changed(V.ISOPODA / "_Isopoda Index.md", master)

    print("Indexes: %d suborders, %d families, %d genera, %d species. %d notes written/updated."
          % (len(tree), tot_fam, tot_gen, tot_sp, wrote))


if __name__ == "__main__":
    main()
