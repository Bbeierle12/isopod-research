# -*- coding: utf-8 -*-
"""Generate Obsidian views from the canonical data/isopods.json.

  * Hobby/<Genus>/<form>.md          one note per form (species or sp.)
  * Hobby/<Genus>/<form> - <morph>.md  one note per morph sub-record
  * Hobby/_Hobby Catalog.md          master index grouped by genus
  * data/isopods.csv                 flat export

Idempotent: on an existing note only the frontmatter block is rewritten, and
only generator-MANAGED keys change. Husbandry keys and the note body (your
prose) are preserved verbatim."""
import os, json, re, csv

VAULT = r"C:\Users\Bbeie\Downloads\Insect and Reptile research"
DATA = os.path.join(VAULT, "data", "isopods.json")
HOBBY = os.path.join(VAULT, "Hobby")

# keys the generator owns (rewritten every run, in this order)
MANAGED = ["id","record_type","family","genus","species","scientificName","is_described",
           "gbif_id","gbif_url","taxon_status","accepted_name","authority","trade_name",
           "locality","morph_name","parent","conglobation","verified_on","tags"]
# user-owned keys: seeded blank on creation, never overwritten afterward
HUSBANDRY = ["common_name","adult_size_mm","origin_region","temperature_c","humidity",
             "substrate","difficulty","bioactive_use","sources"]

def safe(n):
    return re.sub(r'[\\/:*?"<>|]', "-", n).strip()

def form_display(r):
    if r["is_described"]:
        return "%s %s" % (r["genus"], r["species"])
    return '%s sp. "%s"' % (r["genus"], r["trade_name"]) if r["trade_name"] else "%s sp." % r["genus"]

def form_stem(r):
    if r["is_described"]:
        return "%s %s" % (r["genus"], r["species"])
    return ("%s sp. %s" % (r["genus"], r["trade_name"])) if r["trade_name"] else "%s sp." % r["genus"]

def emit_val(v):
    if isinstance(v, bool): return "true" if v else "false"
    if v is None or v == "": return ""
    if isinstance(v, list):
        return "[" + ", ".join(str(x) for x in v) + "]"
    s = str(v)
    if re.search(r'[:#\[\]{}",]', s) or s != s.strip():
        return '"%s"' % s.replace('"', '\\"')
    return s

def split_note(text):
    """Return (frontmatter_dict_ordered, body). Frontmatter parsed as key->raw string."""
    if text.startswith("---"):
        m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
        if m:
            fm_raw, body = m.group(1), m.group(2)
            fm = {}
            for line in fm_raw.splitlines():
                mm = re.match(r"^([A-Za-z0-9_]+):\s?(.*)$", line)
                if mm:
                    fm[mm.group(1)] = mm.group(2)
            return fm, body
    return {}, text

def build_frontmatter(managed_vals, preserved):
    lines = ["---"]
    for k in MANAGED:
        if k in managed_vals:
            v = emit_val(managed_vals[k])
            if v != "" or k in ("trade_name","locality","morph_name","accepted_name"):
                if v == "" and k in ("accepted_name","parent","morph_name","trade_name","locality"):
                    continue
                lines.append("%s: %s" % (k, v))
    for k in HUSBANDRY:
        lines.append("%s: %s" % (k, preserved.get(k, "")))
    # any other user-added keys we don't recognise -> keep
    for k, v in preserved.items():
        if k in HUSBANDRY or k in MANAGED: continue
        lines.append("%s: %s" % (k, v))
    lines.append("---")
    return "\n".join(lines)

def taxonomy_link(r):
    if r["record_type"] == "form" and r["is_described"]:
        if r["taxon_status"] == "accepted":
            return "[[%s %s]]" % (r["genus"], r["species"])
        if r["taxon_status"] == "synonym" and r.get("accepted_name"):
            return "[[%s]] _(accepted name; hobby uses %s)_" % (r["accepted_name"], r["species"])
    return "[[_%s]]" % r["genus"]  # genus index (may be unresolved for hobby-only genera)

def body_template(r):
    if r["record_type"] == "morph":
        head = "# %s — %s" % (form_display_from_parent(r), r["morph_name"])
        rel = "**Morph of** [[%s]]" % form_stem_parent(r)
    else:
        head = "# %s" % form_display(r)
        rel = "**Taxonomy** %s" % taxonomy_link(r)
    return ("%s\n\n%s · **Conglobation:** %s\n\n"
            "## Overview\n\n\n## Appearance\n\n\n## Husbandry\n\n\n"
            "## Lineage & source\n\n\n## References\n") % (head, rel, r["conglobation"])

PARENTS = {}  # id -> form record (filled in main)
def form_display_from_parent(r):
    p = PARENTS.get(r["parent_id"]); return form_display(p) if p else r["genus"]
def form_stem_parent(r):
    p = PARENTS.get(r["parent_id"]); return form_stem(p) if p else r["genus"]

def upsert(path, r):
    managed = {
        "id": r["id"], "record_type": r["record_type"], "family": r["family"],
        "genus": r["genus"], "species": r["species"],
        "scientificName": form_display(r) if r["record_type"]=="form" else
                          "%s '%s'" % (form_stem_parent(r), r["morph_name"]),
        "is_described": r["is_described"], "gbif_id": r.get("gbif_id"),
        "gbif_url": ("https://www.gbif.org/species/%s" % r["gbif_id"]) if r.get("gbif_id") else "",
        "taxon_status": r["taxon_status"], "accepted_name": r.get("accepted_name",""),
        "authority": r.get("authority",""), "trade_name": r.get("trade_name",""),
        "locality": r.get("locality",""), "morph_name": r.get("morph_name",""),
        "parent": r.get("parent_id","") or "", "conglobation": r["conglobation"],
        "verified_on": r.get("verified_on",""),
        "tags": ["isopod","hobby", r["family"].lower(),
                 "described" if r["is_described"] else "provisional",
                 r["record_type"]],
    }
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            fm, body = split_note(f.read())
        preserved = {k: v for k, v in fm.items() if k not in MANAGED}
    else:
        preserved, body = {}, "\n" + body_template(r)
    text = build_frontmatter(managed, preserved) + "\n" + body
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def main():
    with open(DATA, "r", encoding="utf-8") as f:
        records = json.load(f)["records"]
    forms = [r for r in records if r["record_type"] == "form"]
    morphs = [r for r in records if r["record_type"] == "morph"]
    for r in forms: PARENTS[r["id"]] = r

    for r in forms:
        upsert(os.path.join(HOBBY, safe(r["genus"]), safe(form_stem(r)) + ".md"), r)
    for r in morphs:
        p = PARENTS.get(r["parent_id"])
        stem = "%s - %s" % (form_stem(p) if p else r["genus"], r["morph_name"])
        upsert(os.path.join(HOBBY, safe(r["genus"]), safe(stem) + ".md"), r)

    # ---- catalog index ----
    from collections import defaultdict
    bygen = defaultdict(list)
    for r in forms: bygen[r["genus"]].append(r)
    genera = sorted(bygen)
    nd = sum(1 for r in forms if r["is_described"])
    L = ["---","type: index","category: hobby-catalog",
         "form_count: %d" % len(forms), "morph_count: %d" % len(morphs),
         "genus_count: %d" % len(genera),
         "tags: [isopod, hobby, catalog]","---","",
         "# Hobby Isopod Master Catalog","",
         "Generated from `data/isopods.json`. **%d forms** (%d described, %d provisional trade forms) "
         "+ **%d morphs** across **%d genera**." % (len(forms), nd, len(forms)-nd, len(morphs), len(genera)),
         "",
         "> [!info] Taxonomy vs. hobby nomenclature",
         "> Described species are verified against GBIF (`taxon_status: accepted`). Synonyms keep the "
         "hobby's working name with the accepted name recorded. Undescribed imports are `provisional` "
         "trade forms with no scientific name. Regenerate with `scripts/validate.py` + `scripts/generate.py`.",
         ""]
    for g in genera:
        items = sorted(bygen[g], key=lambda r: (not r["is_described"], r["species"], r["trade_name"]))
        L.append("## %s" % g)
        L.append("")
        L.append("| Form | Status | Described | Conglob. | Morphs | GBIF |")
        L.append("|---|---|---|---|---|---|")
        for r in items:
            nm = form_stem(r)
            nmorph = sum(1 for m in morphs if m["parent_id"] == r["id"])
            gb = "[%s](https://www.gbif.org/species/%s)" % (r["gbif_id"], r["gbif_id"]) if r.get("gbif_id") else "—"
            L.append("| [[%s]] | %s | %s | %s | %s | %s |" % (
                nm, r["taxon_status"], "yes" if r["is_described"] else "no",
                r["conglobation"], nmorph or "—", gb))
        L.append("")
    with open(os.path.join(HOBBY, "_Hobby Catalog.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # ---- CSV export ----
    cols = ["id","record_type","family","genus","species","is_described","taxon_status",
            "accepted_name","authority","gbif_id","trade_name","locality","morph_name",
            "parent_id","conglobation"]
    with open(os.path.join(VAULT, "data", "isopods.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in records:
            w.writerow([r.get(c, "") for c in cols])

    print("generated %d form notes + %d morph notes, catalog, and CSV across %d genera."
          % (len(forms), len(morphs), len(genera)))

if __name__ == "__main__":
    main()
