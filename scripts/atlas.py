# -*- coding: utf-8 -*-
"""Isopod Atlas — facet & pattern cross-reference over the Isopoda vault.

Two kinds of filter, at two scopes:
  * RESEARCH axes (ecomorph, terrestrialization, habitat stratum, trophic guild,
    reproduction) plus REALM span the whole Isopoda taxonomy. Fields are
    scaffolded blank on every species note and populated only where we have data
    (data/ecology.json, species-level) — "blank until researched", no
    family-level guessing. Studied taxa carry a/b/c evidence grades. Ecomorph and
    terrestrialization are terrestrial-isopod concepts (Schmalfuss); their maps
    are labelled accordingly.
  * HUSBANDRY facets (size, biome, region, moisture, difficulty, bioactive role,
    taxon status) depend on care data and stay scoped to the hobby forms.

Run after generate.py:  seed -> validate -> husbandry -> generate -> atlas
    python scripts/atlas.py [--dry-run]

Python 3.9+.
"""
import argparse
import json
import os
import re
from collections import Counter, defaultdict

import _vault as V

VAULT = str(V.VAULT)
ISOPODA = str(V.ISOPODA)
ONISCIDEA = os.path.join(ISOPODA, "Oniscidea")
HOBBY = str(V.HOBBY)
MAPS = str(V.MAPS)
safe = V.safe

_SRC = json.loads((V.DATA / "isopoda_suborders.json").read_text(encoding="utf-8"))
GEN = _SRC.get("_generated", "GBIF Backbone Taxonomy")

DRY = False  # set by main(); when True no file is written

# research-filter fields scaffolded onto every species note
RESEARCH_FIELDS = ["ecomorph", "conglobation_type", "terrestrialization",
                   "habitat_stratum", "trophic_guild", "reproduction_mode", "ecology_evidence"]


def _write(path, text):
    return False if DRY else V.write_if_changed(path, text)


# ---------- note-path resolution (mirrors generate.py) ----------
def taxonomy_path(r):
    if r["taxon_status"] == "accepted":
        g, s, f = r["genus"], r["species"], r["family"]
    elif r["taxon_status"] == "synonym" and r.get("accepted_name"):
        p = r["accepted_name"].split(" ", 1); g = p[0]; s = p[1] if len(p) > 1 else r["species"]; f = r["family"]
    else:
        return None
    return os.path.join(ONISCIDEA, safe(f), safe(g), safe("%s %s" % (g, s)) + ".md")


def form_stem(r):
    if r["is_described"]:
        return "%s %s" % (r["genus"], r["species"])
    return ("%s sp. %s" % (r["genus"], r["trade_name"])) if r["trade_name"] else "%s sp." % r["genus"]


def note_path(r):
    tp = taxonomy_path(r)
    if r["is_described"] and tp and os.path.exists(tp):
        return tp
    return os.path.join(HOBBY, safe(r["genus"]), safe(form_stem(r)) + ".md")


# ---------- husbandry-derived facets ----------
def size_class(v):
    nums = [int(x) for x in re.findall(r"\d+", v or "")]
    if not nums: return ""
    m = max(nums)
    return "Micro" if m <= 5 else "Small" if m <= 10 else "Medium" if m <= 15 else "Large"


def biome(origin, humidity):
    o = (origin or "").lower()
    if "desert" in o: return "Desert"
    if any(k in o for k in ["coast", "littoral", "atlantic", "pacific coast", "beach", "tyrrhenian", "restinga", "dune"]): return "Coastal"
    if any(k in o for k in ["se asia", "pantropical", "tropic", "indo-pacific", "caribbean", "philippines", "subtropical", "australia"]): return "Tropical"
    if any(k in o for k in ["mediterranean", "iberia", "spain", "greece", "balkan", "corsica", "sardinia", "italy", "levant", "morocco", "n africa"]): return "Mediterranean"
    return "Temperate"


def region(origin):
    o = (origin or "").lower()
    if any(k in o for k in ["cosmopolitan", "pantropical", "holarctic", "introduced widely"]): return "Cosmopolitan"
    if any(k in o for k in ["arizona", "usa", "americas", "florida", "caribbean", "california", "mexic", "brazil", "argentin",
                            "peru", "chile", "uruguay", "bolivia", "ecuador", "colombia", "venezuela", "neotropic",
                            "central america", "south america", "panama", "costa rica"]): return "Americas"
    if any(k in o for k in ["australia", "new zealand", "tasmania"]): return "Australasia"
    if any(k in o for k in ["philippines", "se asia", "indo-pacific", "central asian", "levant", "middle east", " asia", "asia)"]): return "Asia & Middle East"
    if "morocco" in o or "n africa" in o: return "North Africa"
    if "africa" in o: return "Sub-Saharan Africa"
    if any(k in o for k in ["europe", "mediterranean", "iberia", "spain", "greece", "balkan", "corsica", "sardinia", "italy", "france"]): return "Europe & Mediterranean"
    if any(k in o for k in ["tropic", "pantropical"]): return "Cosmopolitan"
    return "Other"


def moisture(humidity):
    h = (humidity or "").lower()
    if any(k in h for k in ["high", "moist", "wet"]): return "Humid"
    if any(k in h for k in ["dry", "arid", "ventilat"]): return "Arid"
    return "Moderate"


def difficulty_tier(d):
    d = (d or "").lower()
    if d in ("beginner", "beginner-intermediate"): return "Beginner"
    if d == "intermediate": return "Intermediate"
    if d in ("intermediate-advanced", "advanced"): return "Advanced"
    return ""


def bioactive_role(b):
    b = (b or "").lower()
    if not b: return ""
    if any(k in b for k in ["not a", "specialist", "myrmecophile", "coastal", "desert"]): return "Specialist"
    if "micro" in b: return "Micro-cleanup"
    if "feeder" in b: return "Feeder"
    if "cleanup" in b: return "Cleanup crew"
    if "display" in b: return "Display"
    return "Display"


def conglob_label(c):
    return {"FULL": "Roller", "PARTIAL": "Partial roller", "NONE": "Non-roller"}.get(c, "")


def taxon_group(r):
    if not r["is_described"]: return "Undescribed (provisional)"
    return "Described" if r["taxon_status"] in ("accepted", "synonym") else "Unresolved"


def norm_trophic(v):
    v = (v or "").lower()
    if not v: return ""
    if "wood" in v and "bor" in v: return "Wood-borer"
    if "parasit" in v: return "Parasite (ectoparasite)"
    if any(k in v for k in ["predator", "scaveng", "micropred"]): return "Micropredator/scavenger"
    if any(k in v for k in ["filter", "deposit-feed", "suspension"]): return "Filter/deposit-feeder"
    if "algivore" in v: return "Algivore/detritivore"
    if "coprophage" in v: return "Detritivore/coprophage"
    if "assumed" in v: return "Detritivore (assumed/unstudied)"
    if "herbivore" in v: return "Detritivore (+herbivore)"
    return "General detritivore"


def norm_repro(v):
    v = (v or "").lower()
    if not v: return ""
    if "subsocial" in v: return "Subsocial (biparental)"
    # Parthenogenetic only when genuinely so — never on a negation ("not
    # parthenogenetic") or a hedge ("parthenogenesis suspected/possible").
    if "parthenogen" in v and not re.search(r"\bnot\b|suspect|possibl|unconfirm|unlikely", v):
        return "Parthenogenetic"
    if "assumed" in v: return "Sexual (assumed)"
    return "Sexual"


def stratum_primary(v):
    return (v or "").split("/")[0].strip()


# ---------- frontmatter writers (delegate to the shared, correct primitives) ----------
def set_fields(path, fields):
    """Overwrite/insert each field. Block-valued keys and blank values are left
    untouched; the write is atomic and skipped when nothing changed."""
    t = V.read_text(path)
    parsed = V.parse_frontmatter(t) if t is not None else None
    if not parsed: return
    o, fm, c, body = parsed
    for k, val in fields.items():
        fm = V.set_field(fm, k, val)
    _write(path, o + fm + c + body)


def scaffold_fields(path, fields):
    """Ensure every RESEARCH_FIELD exists (blank ok); fill a blank one only when
    we have data. Hand-entered values always win."""
    t = V.read_text(path)
    parsed = V.parse_frontmatter(t) if t is not None else None
    if not parsed: return
    o, fm, c, body = parsed
    for k in RESEARCH_FIELDS:
        fm = V.ensure_field(fm, k, fields.get(k, ""))
    _write(path, o + fm + c + body)


# ---------- load ----------
with open(os.path.join(VAULT, "data", "isopods.json"), "r", encoding="utf-8") as f:
    records = json.load(f)["records"]
with open(os.path.join(VAULT, "data", "ecology.json"), "r", encoding="utf-8") as f:
    _eco_doc = json.load(f)
eco = _eco_doc["entries"]
ECO_REFS = _eco_doc.get("references", {})
eco_exact = {e["match"]: e for e in eco if not e["match"].endswith(" *")}
eco_genus = {e["match"][:-2]: e for e in eco if e["match"].endswith(" *")}


def research_for(r):
    return eco_exact.get("%s %s" % (r["genus"], r["species"])) or eco_genus.get(r["genus"])


def research_row(display, family, e, realm="terrestrial"):
    evd = e.get("evd", {}) if e else {}
    e = e or {}
    return {"display": display, "link": "[[%s]]" % display, "family": family, "realm": realm,
            "ecomorph": e.get("ecomorph", ""), "terrestrialization": e.get("terrestrialization", ""),
            "stratum": e.get("stratum", ""), "trophic": e.get("trophic", ""), "reproduction": e.get("reproduction", ""),
            "evd_stratum": evd.get("stratum", ""), "evd_trophic": evd.get("trophic", ""), "evd_life": evd.get("life", "")}


def eco_evidence(e):
    d = e.get("evd", {})
    s = "stratum:%s trophic:%s life:%s" % (d.get("stratum", "?"), d.get("trophic", "?"), d.get("life", "?"))
    refs = e.get("source_refs") or []
    return "%s refs:%s" % (s, ",".join(refs)) if refs else s


def eco_sources(e):
    """Rendered citation list for a species' ecology claims (empty when the
    entry has no verifiable published source)."""
    return [ECO_REFS[k]["citation"] for k in (e.get("source_refs") or []) if k in ECO_REFS]


RESEARCH_KEYS = ("ecomorph", "terrestrialization", "stratum", "trophic", "reproduction")


def is_graded(row):
    """A row is 'classified' (studied) only if it carries at least one populated
    research axis — realm alone does not count."""
    return any(row[k] for k in RESEARCH_KEYS)


# ---------- map builder ----------
def facet_map(fname, title, key, order, data, denom_label, graded=False, evd_key=None, norm=None, subtitle=""):
    val = (lambda row: (norm(row[key]) if norm else row[key]))
    groups = defaultdict(list)
    for row in data:
        v = val(row)
        if v: groups[v].append(row)
    ordered = [c for c in order if c in groups] + sorted(c for c in groups if c not in order)
    n = sum(len(groups[c]) for c in ordered)
    L = ["---", "type: facet-map", "facet: %s" % key, "tags: [isopod, atlas, facet-map]", "---", "",
         "# %s" % title, "", subtitle, "",
         "**%d %s classified.**%s ← [[_Isopod Atlas]]" %
         (n, denom_label, "  Research axis — evidence-graded; the rest await study." if graded else ""), ""]
    for c in ordered:
        items = sorted(groups[c], key=lambda r: r["display"])
        L += ["## %s  <small>(%d)</small>" % (c, len(items)), ""]
        if graded and evd_key:
            L += ["| Species | Family | Detail | Evd |", "|---|---|---|---|"]
            L += ["| %s | %s | %s | %s |" % (r["link"], r["family"], r[key], r.get(evd_key, "") or "—") for r in items]
        else:
            L += ["| Species | Family |", "|---|---|"] + ["| %s | %s |" % (r["link"], r["family"]) for r in items]
        L.append("")
    _write(os.path.join(MAPS, fname), "\n".join(L) + "\n")
    return title, fname, n


def crosstab(data, rowkey, colkey, roworder, colorder, rnorm=None, cnorm=None):
    rv = (lambda r: (rnorm(r[rowkey]) if rnorm else r[rowkey])); cv = (lambda r: (cnorm(r[colkey]) if cnorm else r[colkey]))
    rp = [c for c in roworder if any(rv(r) == c for r in data)] + sorted({rv(r) for r in data if rv(r) and rv(r) not in roworder})
    cp = [c for c in colorder if any(cv(r) == c for r in data)] + sorted({cv(r) for r in data if cv(r) and cv(r) not in colorder})
    cnt = Counter((rv(r), cv(r)) for r in data if rv(r) and cv(r))
    out = ["| %s ↓ / %s → | %s | **Σ** |" % (rowkey, colkey, " | ".join(cp)), "|" + "---|" * (len(cp) + 2)]
    coltot = Counter()
    for rc in rp:
        cells, tot = [], 0
        for cc in cp:
            n = cnt[(rc, cc)]; tot += n; coltot[cc] += n; cells.append(str(n) if n else "·")
        out.append("| **%s** | %s | **%s** |" % (rc, " | ".join(cells), tot))
    out.append("| **Σ** | %s | **%d** |" % (" | ".join("**%d**" % coltot[c] for c in cp), sum(coltot.values())))
    return "\n".join(out)


def run():
    forms = [r for r in records if r["record_type"] == "form"]

    # ---- Pass 1: hobby forms — husbandry facets + research + frontmatter ----
    rows = []
    for r in forms:
        e = research_for(r)
        fac = {
            "conglobation_type": conglob_label(r.get("conglobation", "")), "size_class": size_class(r.get("adult_size_mm", "")),
            "biome": biome(r.get("origin_region", ""), r.get("humidity", "")), "biogeo_region": region(r.get("origin_region", "")),
            "moisture": moisture(r.get("humidity", "")), "difficulty_tier": difficulty_tier(r.get("difficulty", "")),
            "bioactive_role": bioactive_role(r.get("bioactive_use", "")), "taxon_group": taxon_group(r),
        }
        rows.append({"display": form_stem(r), "link": "[[%s]]" % form_stem(r), "family": r["family"], **fac})
        set_fields(note_path(r), {
            "conglobation_type": fac["conglobation_type"], "size_class": fac["size_class"], "biome": fac["biome"],
            "biogeo_region": fac["biogeo_region"], "moisture": fac["moisture"], "difficulty_tier": fac["difficulty_tier"],
            "bioactive_role": fac["bioactive_role"],
            "ecomorph": e.get("ecomorph", "") if e else "", "terrestrialization": e.get("terrestrialization", "") if e else "",
            "habitat_stratum": e.get("stratum", "") if e else "", "trophic_guild": e.get("trophic", "") if e else "",
            "reproduction_mode": e.get("reproduction", "") if e else "", "ecology_evidence": eco_evidence(e) if e else "",
        })

    # ---- Pass 2: scaffold research fields onto EVERY Isopoda species note ----
    tax_species = []   # (name, family, path)
    for dirpath, _, files in os.walk(ISOPODA):
        for fn in files:
            if fn.endswith(".md") and not fn.startswith("_"):
                name = fn[:-3]
                family = os.path.basename(os.path.dirname(os.path.dirname(os.path.join(dirpath, fn))))
                tax_species.append((name, family, os.path.join(dirpath, fn)))

    scaffolded = 0
    rrows = []          # research rows spanning the taxonomy
    for name, family, path in tax_species:
        e = eco_exact.get(name)   # species-level only — no family/genus guessing on the taxonomy
        t = V.read_text(path)
        if t is None:
            continue
        # Read realm from the frontmatter only, tolerating a quote and a blank
        # value (the old \s* regex ran across the newline into the next key).
        parsed = V.parse_frontmatter(t)
        fm = parsed[1] if parsed else ""
        rm = re.search(r'^realm:[ \t]*"?([A-Za-z]+)', fm, re.M)
        realm = rm.group(1).lower() if rm else "terrestrial"
        vals = {"ecomorph": e.get("ecomorph", "") if e else "", "conglobation_type": "",
                "terrestrialization": e.get("terrestrialization", "") if e else "",
                "habitat_stratum": e.get("stratum", "") if e else "", "trophic_guild": e.get("trophic", "") if e else "",
                "reproduction_mode": e.get("reproduction", "") if e else "", "ecology_evidence": eco_evidence(e) if e else ""}
        scaffold_fields(path, vals)
        if not rm:
            set_fields(path, {"realm": realm})
        scaffolded += 1
        rrows.append(research_row(name, family, e, realm))   # e may be None (blank row)

    # provisional hobby forms carry genus-level research (evidence-graded)
    for r in forms:
        if not r["is_described"]:
            e = research_for(r)
            if e:
                rrows.append(research_row(form_stem(r), r["family"], e))

    if not DRY:
        V.MAPS.mkdir(parents=True, exist_ok=True)

    classified = sum(1 for r in rrows if is_graded(r))   # genuinely studied taxa
    NH = "hobby forms"
    NT = "of %d Isopoda species" % len(rrows)             # denom matches the rendered pool

    # husbandry facets — scoped to hobby forms
    husb = []
    husb.append(facet_map("By Conglobation.md", "By Conglobation", "conglobation_type", ["Roller", "Partial roller", "Non-roller"], rows, NH, subtitle="Schmalfuss defense axis (hobby forms; not yet coded taxonomy-wide)."))
    husb.append(facet_map("By Size Class.md", "By Size Class", "size_class", ["Micro", "Small", "Medium", "Large"], rows, NH, subtitle="Adult length: Micro ≤5 · Small 6–10 · Medium 11–15 · Large >15 mm."))
    husb.append(facet_map("By Biome.md", "By Biome", "biome", ["Temperate", "Mediterranean", "Tropical", "Desert", "Coastal"], rows, NH, subtitle="Climate zone (husbandry-derived)."))
    husb.append(facet_map("By Region.md", "By Region", "biogeo_region", ["Europe & Mediterranean", "North Africa", "Sub-Saharan Africa", "Asia & Middle East", "Americas", "Australasia", "Cosmopolitan", "Other"], rows, NH, subtitle="Biogeographic origin (husbandry-derived)."))
    husb.append(facet_map("By Moisture.md", "By Moisture Regime", "moisture", ["Arid", "Moderate", "Humid"], rows, NH, subtitle="Husbandry moisture requirement."))
    husb.append(facet_map("By Difficulty.md", "By Difficulty", "difficulty_tier", ["Beginner", "Intermediate", "Advanced"], rows, NH, subtitle="Keeping difficulty."))
    husb.append(facet_map("By Bioactive Role.md", "By Bioactive Role", "bioactive_role", ["Cleanup crew", "Micro-cleanup", "Feeder", "Display", "Specialist"], rows, NH, subtitle="Role in a bioactive setup."))
    husb.append(facet_map("By Taxon Status.md", "By Taxon Status", "taxon_group", ["Described", "Undescribed (provisional)", "Unresolved"], rows, NH, subtitle="Science ↔ hobby naming gap."))

    # taxonomy-wide axes — span all Isopoda. Realm is not evidence-graded.
    res = []
    res.append(facet_map("By Realm.md", "By Realm", "realm", ["terrestrial", "littoral", "brackish", "freshwater", "interstitial", "marine"], rrows, NT, False, None, None, "Broad environmental realm (from the WoRMS-sourced family map)."))
    res.append(facet_map("By Ecomorph Type.md", "By Ecomorph Type", "ecomorph", ["Runner", "Clinger", "Roller", "Creeper", "Spiny", "Non-conformist"], rrows, NT, True, "evd_stratum", None, "Schmalfuss (1984) ecomorphological strategy — a terrestrial-isopod axis."))
    res.append(facet_map("By Terrestrialization.md", "By Terrestrialization", "terrestrialization", ["littoral", "hygrophilous", "mesophilous", "xerophilous"], rrows, NT, True, "evd_stratum", None, "Degree of independence from water — a terrestrial-isopod axis."))
    res.append(facet_map("By Habitat Stratum.md", "By Habitat Stratum", "stratum", ["EN", "EP", "CO", "AR", "CA", "LI", "SA", "MY", "BE", "PE", "IN", "WB", "HA", "GW"], rrows, NT, True, "evd_stratum", stratum_primary, "EN soil · EP surface/litter · CO bark · CA cave · LI littoral · SA rock · MY ant-nest · BE benthic · PE pelagic · IN interstitial · WB wood-boring · HA host-associated · GW groundwater."))
    res.append(facet_map("By Trophic Guild.md", "By Trophic Guild", "trophic", ["General detritivore", "Detritivore/coprophage", "Detritivore (+herbivore)", "Algivore/detritivore", "Wood-borer", "Micropredator/scavenger", "Parasite (ectoparasite)", "Filter/deposit-feeder", "Detritivore (assumed/unstudied)"], rrows, NT, True, "evd_trophic", norm_trophic, "Feeding guild."))
    res.append(facet_map("By Reproduction.md", "By Reproduction", "reproduction", ["Sexual", "Sexual (assumed)", "Parthenogenetic", "Subsocial (biparental)"], rrows, NT, True, "evd_life", norm_repro, "Reproductive mode / life-history highlight."))

    # ---- patterns ----
    P = ["---", "type: patterns", "tags: [isopod, atlas, patterns]", "---", "", "# Isopod Atlas — Pattern Matrices", "",
         "Counts; `·` = none. ← [[_Isopod Atlas]]", "",
         "> [!note] Scope per matrix", "> Husbandry matrices cover the %d hobby forms; the research matrix (Ecomorph × "
         "Terrestrialization) covers the %d species classified so far. Blank-until-researched: "
         "unclassified species are simply absent." % (len(rows), classified), ""]
    P += ["## Biome × Conglobation  <small>(hobby)</small>", "", crosstab(rows, "biome", "conglobation_type", ["Temperate", "Mediterranean", "Tropical", "Desert", "Coastal"], ["Roller", "Partial roller", "Non-roller"]), ""]
    P += ["## Family × Difficulty  <small>(hobby)</small>", "", crosstab(rows, "family", "difficulty_tier", [], ["Beginner", "Intermediate", "Advanced"]), ""]
    P += ["## Region × Size Class  <small>(hobby)</small>", "", crosstab(rows, "biogeo_region", "size_class", ["Europe & Mediterranean", "North Africa", "Sub-Saharan Africa", "Asia & Middle East", "Americas", "Australasia", "Cosmopolitan"], ["Micro", "Small", "Medium", "Large"]), ""]
    P += ["## Biome × Bioactive Role  <small>(hobby)</small>", "", crosstab(rows, "biome", "bioactive_role", ["Temperate", "Mediterranean", "Tropical", "Desert", "Coastal"], ["Cleanup crew", "Micro-cleanup", "Feeder", "Display", "Specialist"]), ""]
    P += ["## Ecomorph × Terrestrialization  <small>(research, terrestrial)</small>", "", crosstab(rrows, "ecomorph", "terrestrialization", ["Runner", "Clinger", "Roller", "Creeper", "Spiny", "Non-conformist"], ["littoral", "hygrophilous", "mesophilous", "xerophilous"]), ""]
    _write(os.path.join(MAPS, "Patterns.md"), "\n".join(P) + "\n")

    # ---- hub ----
    H = ["---", "type: index", "category: atlas-hub", "tags: [isopod, atlas, moc]", "---", "", "# Isopod Atlas", "",
         "Facet & pattern cross-reference. **Realm and research axes span all %d Isopoda species** (hobby + non-hobby); "
         "**husbandry facets** cover the %d hobby forms. Generated by `scripts/atlas.py` (%s)." % (len(tax_species), len(rows), GEN), "",
         "> [!info] Blank until researched", "> Every species note carries the research-filter fields "
         "(ecomorph, terrestrialization, habitat stratum, trophic guild, reproduction), populated only where studied "
         "(%d so far, evidence-graded a/b/c). No family-level guessing — add rows to `data/ecology.json` to classify more." % classified, "",
         "## Taxonomy-wide axes  <small>(all Isopoda)</small>", ""]
    for title, fname, n in res:
        H.append("- [[%s|%s]] — %d classified" % (fname[:-3], title, n))
    H += ["", "## Husbandry facets  <small>(hobby forms)</small>", ""]
    for title, fname, n in husb:
        H.append("- [[%s|%s]] — %d" % (fname[:-3], title, n))
    # sources behind the research axes — every claim in data/ecology.json is
    # either backed by one of these or explicitly marked unsourced
    cited = sorted({k for e in eco for k in (e.get("source_refs") or [])})
    H += ["", "## Sources  <small>(research axes)</small>", "",
          "%d of %d ecology entries cite a published source; the rest are marked "
          "explicitly unsourced in `data/ecology.json` rather than assumed."
          % (sum(1 for e in eco if e.get("source_refs")), len(eco)), ""]
    for k in cited:
        r = ECO_REFS.get(k)
        if not r:
            continue
        doi = " https://doi.org/%s" % r["doi"] if r.get("doi") else ""
        H.append("- %s%s" % (r["citation"], doi))
    H += ["", "## Pattern analysis", "", "- [[Patterns|Pattern matrices]]", "", "## See also", "",
          "- [[_Isopoda Index|Isopoda taxonomy]] · [[_Hobby Catalog|Hobby catalog]]",
          "- [[Isopod Categorization & Research Outline]] · [[Isopod Species Ecology Data]]", ""]
    _write(os.path.join(MAPS, "_Isopod Atlas.md"), "\n".join(H) + "\n")

    print("Atlas: %d husbandry + %d taxonomy-wide maps + Patterns + hub.%s"
          % (len(husb), len(res), "  [DRY RUN]" if DRY else ""))
    print("Scaffolded research fields onto %d species notes; %d studied (evidence-graded)." % (scaffolded, classified))


def main():
    global DRY
    ap = argparse.ArgumentParser(description="Build the Isopod Atlas facet maps, patterns and hub.")
    ap.add_argument("--dry-run", action="store_true", help="compute everything but write nothing")
    DRY = ap.parse_args().dry_run
    run()


if __name__ == "__main__":
    main()
