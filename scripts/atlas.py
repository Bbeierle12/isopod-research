# -*- coding: utf-8 -*-
"""Isopod Atlas — build the facet & pattern cross-reference layer.

Reads data/isopods.json (husbandry) + data/ecology.json (research axes), derives
facets, writes facet frontmatter onto each species' note, and generates Maps/:
one MOC per facet, a Patterns.md cross-tab dashboard, and the _Isopod Atlas hub.

Run after generate.py:  seed -> validate -> husbandry -> generate -> atlas
Scope: the 112 hobby *form* records (88 described + 24 provisional). Morphs inherit
their parent and are omitted from the facet tables. Husbandry facets are derived for
all forms; research axes only where ecology.json has data (with a/b/c evidence grades)."""
import os, re, json
from collections import defaultdict, Counter

VAULT = r"C:\Users\Bbeie\Downloads\Insect and Reptile research"
ONISCIDEA = os.path.join(VAULT, "Oniscidea")
HOBBY = os.path.join(VAULT, "Hobby")
MAPS = os.path.join(VAULT, "Maps")
GEN = "2026-07-25"

def safe(n):
    return re.sub(r'[\\/:*?"<>|]', "-", n).strip()

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
    if any(k in o for k in ["arizona", "usa", "americas", "florida", "caribbean"]): return "Americas"
    if "australia" in o: return "Australasia"
    if any(k in o for k in ["philippines", "se asia", "indo-pacific", "central asian", "levant", "middle east", " asia"]): return "Asia & Middle East"
    if "morocco" in o or "n africa" in o: return "North Africa"
    if "africa" in o: return "Sub-Saharan Africa"
    if any(k in o for k in ["europe", "mediterranean", "iberia", "spain", "greece", "balkan", "corsica", "sardinia", "italy", "france", "atlantic"]): return "Europe & Mediterranean"
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
    ts = r["taxon_status"]
    if not r["is_described"]: return "Undescribed (provisional)"
    if ts in ("accepted", "synonym"): return "Described"
    return "Unresolved"

# research-axis normalizers (for cleaner grouping)
def norm_trophic(v):
    v = (v or "").lower()
    if not v: return ""
    if "algivore" in v: return "Algivore/detritivore"
    if "coprophage" in v: return "Detritivore/coprophage"
    if "assumed" in v: return "Detritivore (assumed/unstudied)"
    if "herbivore" in v: return "Detritivore (+herbivore)"
    return "General detritivore"

def norm_repro(v):
    v = (v or "").lower()
    if not v: return ""
    if "parthenogen" in v: return "Parthenogenetic"
    if "subsocial" in v: return "Subsocial (biparental)"
    if "assumed" in v: return "Sexual (assumed)"
    return "Sexual"

def stratum_primary(v):
    return (v or "").split("/")[0].strip()

# ---------- frontmatter writer (overwrite/add facet keys) ----------
def set_fields(path, fields):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        t = f.read()
    m = re.match(r"^(---\r?\n)(.*?\r?\n)(---\r?\n)(.*)$", t, re.S)
    if not m:
        return
    fm = m.group(2)
    for k, v in fields.items():
        if v == "" or v is None:
            continue
        val = ('"%s"' % v) if re.search(r'[:#\[\],]', str(v)) else str(v)
        if re.search(r"^%s:" % re.escape(k), fm, re.M):
            fm = re.sub(r"^%s:.*$" % re.escape(k), "%s: %s" % (k, val), fm, count=1, flags=re.M)
        else:
            mt = re.search(r"^tags:", fm, re.M)
            line = "%s: %s\n" % (k, val)
            fm = (fm[:mt.start()] + line + fm[mt.start():]) if mt else (fm + line)
    new = m.group(1) + fm + m.group(3) + m.group(4)
    if new != t:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)

# ---------- load ----------
with open(os.path.join(VAULT, "data", "isopods.json"), "r", encoding="utf-8") as f:
    records = json.load(f)["records"]
with open(os.path.join(VAULT, "data", "ecology.json"), "r", encoding="utf-8") as f:
    eco = json.load(f)["entries"]
eco_exact = {e["match"]: e for e in eco if not e["match"].endswith(" *")}
eco_genus = {e["match"][:-2]: e for e in eco if e["match"].endswith(" *")}

def research_for(r):
    key = "%s %s" % (r["genus"], r["species"])
    return eco_exact.get(key) or eco_genus.get(r["genus"])

forms = [r for r in records if r["record_type"] == "form"]

# ---------- compute facets + write to notes ----------
rows = []  # one dict per form: display, link, family, + all facet values
for r in forms:
    e = research_for(r)
    evd = e.get("evd", {}) if e else {}
    fac = {
        "conglobation_type": conglob_label(r.get("conglobation", "")),
        "size_class": size_class(r.get("adult_size_mm", "")),
        "biome": biome(r.get("origin_region", ""), r.get("humidity", "")),
        "biogeo_region": region(r.get("origin_region", "")),
        "moisture": moisture(r.get("humidity", "")),
        "difficulty_tier": difficulty_tier(r.get("difficulty", "")),
        "bioactive_role": bioactive_role(r.get("bioactive_use", "")),
        "taxon_group": taxon_group(r),
        "ecomorph": e.get("ecomorph", "") if e else "",
        "terrestrialization": e.get("terrestrialization", "") if e else "",
        "stratum": e.get("stratum", "") if e else "",
        "trophic": e.get("trophic", "") if e else "",
        "reproduction": e.get("reproduction", "") if e else "",
        "evd_stratum": evd.get("stratum", ""), "evd_trophic": evd.get("trophic", ""), "evd_life": evd.get("life", ""),
    }
    stem = form_stem(r)
    rows.append({"display": stem, "link": "[[%s]]" % stem, "family": r["family"], "id": r["id"], **fac})
    # write facet frontmatter onto the note
    ecology_evidence = ("stratum:%s trophic:%s life:%s" % (evd.get("stratum", "?"), evd.get("trophic", "?"), evd.get("life", "?"))) if e else ""
    set_fields(note_path(r), {
        "conglobation_type": fac["conglobation_type"], "size_class": fac["size_class"], "biome": fac["biome"],
        "biogeo_region": fac["biogeo_region"], "moisture": fac["moisture"], "difficulty_tier": fac["difficulty_tier"],
        "bioactive_role": fac["bioactive_role"], "ecomorph": fac["ecomorph"],
        "terrestrialization": fac["terrestrialization"], "habitat_stratum": fac["stratum"],
        "trophic_guild": fac["trophic"], "reproduction_mode": fac["reproduction"],
        "ecology_evidence": ecology_evidence,
    })

os.makedirs(MAPS, exist_ok=True)

# ---------- facet-map builder ----------
def facet_map(fname, title, key, order, is_research=False, evd_key=None, norm=None, subtitle=""):
    def val(row):
        v = row[key]
        return norm(v) if norm else v
    groups = defaultdict(list)
    for row in rows:
        v = val(row)
        if v: groups[v].append(row)
    ordered = [c for c in order if c in groups] + sorted(c for c in groups if c not in order)
    n = sum(len(groups[c]) for c in ordered)
    L = ["---", "type: facet-map", "facet: %s" % key, "tags: [isopod, atlas, facet-map]", "---", "",
         "# %s" % title, "", subtitle, "",
         "%d of %d forms classified%s. ← [[_Isopod Atlas]]" %
         (n, len(rows), " (research axis — evidence-graded)" if is_research else ""), ""]
    for c in ordered:
        items = sorted(groups[c], key=lambda r: r["display"])
        L.append("## %s  <small>(%d)</small>" % (c, len(items)))
        L.append("")
        if is_research and evd_key:
            L.append("| Species | Family | Detail | Evd |")
            L.append("|---|---|---|---|")
            for r in items:
                L.append("| %s | %s | %s | %s |" % (r["link"], r["family"], r[key], r.get(evd_key, "") or "—"))
        else:
            L.append("| Species | Family |")
            L.append("|---|---|")
            for r in items:
                L.append("| %s | %s |" % (r["link"], r["family"]))
        L.append("")
    with open(os.path.join(MAPS, fname), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return title, fname, n

MAPDEFS = [
    ("By Conglobation.md", "By Conglobation", "conglobation_type", ["Roller", "Partial roller", "Non-roller"], False, None, None, "Schmalfuss defense axis — ability to roll into a sphere."),
    ("By Size Class.md", "By Size Class", "size_class", ["Micro", "Small", "Medium", "Large"], False, None, None, "Adult length: Micro ≤5 · Small 6–10 · Medium 11–15 · Large >15 mm."),
    ("By Biome.md", "By Biome", "biome", ["Temperate", "Mediterranean", "Tropical", "Desert", "Coastal"], False, None, None, "Climate zone derived from origin + humidity."),
    ("By Region.md", "By Region", "biogeo_region", ["Europe & Mediterranean", "North Africa", "Sub-Saharan Africa", "Asia & Middle East", "Americas", "Australasia", "Cosmopolitan", "Other"], False, None, None, "Biogeographic origin."),
    ("By Moisture.md", "By Moisture Regime", "moisture", ["Arid", "Moderate", "Humid"], False, None, None, "Husbandry moisture requirement."),
    ("By Difficulty.md", "By Difficulty", "difficulty_tier", ["Beginner", "Intermediate", "Advanced"], False, None, None, "Keeping difficulty (collapsed to three tiers)."),
    ("By Bioactive Role.md", "By Bioactive Role", "bioactive_role", ["Cleanup crew", "Micro-cleanup", "Feeder", "Display", "Specialist"], False, None, None, "Functional role in a bioactive setup."),
    ("By Taxon Status.md", "By Taxon Status", "taxon_group", ["Described", "Undescribed (provisional)", "Unresolved"], False, None, None, "Science ↔ hobby naming gap."),
    ("By Ecomorph Type.md", "By Ecomorph Type", "ecomorph", ["Runner", "Clinger", "Roller", "Creeper", "Spiny", "Non-conformist"], True, "evd_stratum", None, "Schmalfuss (1984) ecomorphological strategy — a functional axis."),
    ("By Terrestrialization.md", "By Terrestrialization", "terrestrialization", ["littoral", "hygrophilous", "mesophilous", "xerophilous"], True, "evd_stratum", None, "Degree of independence from water (littoral → xeric)."),
    ("By Habitat Stratum.md", "By Habitat Stratum", "stratum", ["EN", "EP", "CO", "AR", "CA", "LI", "SA", "MY"], True, "evd_stratum", stratum_primary, "EN soil · EP surface/litter · CO bark · CA cave · LI littoral · SA rock · MY ant-nest."),
    ("By Trophic Guild.md", "By Trophic Guild", "trophic", ["General detritivore", "Detritivore/coprophage", "Detritivore (+herbivore)", "Algivore/detritivore", "Detritivore (assumed/unstudied)"], True, "evd_trophic", norm_trophic, "Feeding guild. Terrestrial isopods are NOT true xylophages."),
    ("By Reproduction.md", "By Reproduction", "reproduction", ["Sexual", "Sexual (assumed)", "Parthenogenetic", "Subsocial (biparental)"], True, "evd_life", norm_repro, "Reproductive mode / life-history highlight."),
]
built = [facet_map(*d) for d in MAPDEFS]

# ---------- pattern cross-tabs ----------
def crosstab(rowkey, colkey, roworder, colorder, rnorm=None, cnorm=None):
    rv = (lambda r: (rnorm(r[rowkey]) if rnorm else r[rowkey]))
    cv = (lambda r: (cnorm(r[colkey]) if cnorm else r[colkey]))
    rows_present = [c for c in roworder if any(rv(r) == c for r in rows)] + sorted({rv(r) for r in rows if rv(r) and rv(r) not in roworder})
    cols_present = [c for c in colorder if any(cv(r) == c for r in rows)] + sorted({cv(r) for r in rows if cv(r) and cv(r) not in colorder})
    cnt = Counter((rv(r), cv(r)) for r in rows if rv(r) and cv(r))
    out = ["| %s ↓ / %s → | %s | **Σ** |" % (rowkey, colkey, " | ".join(cols_present))]
    out.append("|" + "---|" * (len(cols_present) + 2))
    coltot = Counter()
    for rc in rows_present:
        cells, tot = [], 0
        for cc in cols_present:
            n = cnt[(rc, cc)]; tot += n; coltot[cc] += n
            cells.append(str(n) if n else "·")
        out.append("| **%s** | %s | **%s** |" % (rc, " | ".join(cells), tot))
    out.append("| **Σ** | %s | **%d** |" % (" | ".join("**%d**" % coltot[c] for c in cols_present), sum(coltot.values())))
    return "\n".join(out)

P = ["---", "type: patterns", "tags: [isopod, atlas, patterns]", "---", "",
     "# Isopod Atlas — Pattern Matrices", "",
     "Cross-tabulations over the %d hobby forms. Counts; `·` = none. ← [[_Isopod Atlas]]" % len(rows), "",
     "> [!note] Read with care", "> Husbandry-derived facets cover all forms; research axes (ecomorph, stratum, "
     "trophic, reproduction) are populated only for studied taxa, so their rows undercount. Evidence "
     "grades live in the individual facet maps.", ""]
CT = [
    ("Biome × Conglobation", "biome", "conglobation_type", ["Temperate","Mediterranean","Tropical","Desert","Coastal"], ["Roller","Partial roller","Non-roller"], None, None),
    ("Family × Difficulty", "family", "difficulty_tier", [], ["Beginner","Intermediate","Advanced"], None, None),
    ("Region × Size Class", "biogeo_region", "size_class", ["Europe & Mediterranean","North Africa","Sub-Saharan Africa","Asia & Middle East","Americas","Australasia","Cosmopolitan"], ["Micro","Small","Medium","Large"], None, None),
    ("Biome × Bioactive Role", "biome", "bioactive_role", ["Temperate","Mediterranean","Tropical","Desert","Coastal"], ["Cleanup crew","Micro-cleanup","Feeder","Display","Specialist"], None, None),
    ("Ecomorph × Terrestrialization", "ecomorph", "terrestrialization", ["Runner","Clinger","Roller","Creeper","Spiny","Non-conformist"], ["littoral","hygrophilous","mesophilous","xerophilous"], None, None),
    ("Taxon status × Biome", "taxon_group", "biome", ["Described","Undescribed (provisional)","Unresolved"], ["Temperate","Mediterranean","Tropical","Desert","Coastal"], None, None),
]
for title, rk, ck, ro, co, rn, cn in CT:
    P.append("## %s" % title); P.append(""); P.append(crosstab(rk, ck, ro, co, rn, cn)); P.append("")
with open(os.path.join(MAPS, "Patterns.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(P) + "\n")

# ---------- hub ----------
H = ["---", "type: index", "category: atlas-hub", "tags: [isopod, atlas, moc]", "---", "",
     "# Isopod Atlas", "",
     "Facet & pattern cross-reference over the **%d hobby forms** (88 described + 24 provisional). "
     "Generated by `scripts/atlas.py` from `data/isopods.json` + `data/ecology.json` on %s." % (len(rows), GEN), "",
     "> [!info] Two kinds of facet", "> **Husbandry-derived** (all forms): conglobation, size, biome, region, moisture, "
     "difficulty, bioactive role, taxon status. **Research axes** (studied taxa, evidence-graded a/b/c): "
     "ecomorph, terrestrialization, habitat stratum, trophic guild, reproduction.", "",
     "## Facet maps", ""]
for title, fname, n in built:
    H.append("- [[%s|%s]] — %d classified" % (fname[:-3], title, n))
H += ["", "## Pattern analysis", "", "- [[Patterns|Pattern matrices]] — cross-tab pivots",
      "", "## See also", "",
      "- [[_Oniscidea Index|Oniscidea taxonomy (4,226 species)]]",
      "- [[_Hobby Catalog|Hobby master catalog]]",
      "- [[Isopod Categorization & Research Outline]] · [[Isopod Species Ecology Data]]", ""]
with open(os.path.join(MAPS, "_Isopod Atlas.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(H) + "\n")

print("Atlas built: %d facet maps + Patterns + hub over %d forms." % (len(built), len(rows)))
print("Research axes populated for %d/%d forms." % (sum(1 for r in rows if r["ecomorph"]), len(rows)))
