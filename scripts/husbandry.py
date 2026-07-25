# -*- coding: utf-8 -*-
"""Populate catalog-level husbandry DEFAULTS in data/isopods.json for the
well-documented hobby forms. These are general hobby-consensus care guidelines,
not per-strain measurements. generate.py copies them into notes only where the
note field is still blank, so any hand-edit you make later always wins.

Idempotent: sets the same defaults each run. Obscure/poorly-documented forms are
intentionally left blank rather than guessed."""
import os, json

VAULT = r"C:\Users\Bbeie\Downloads\Insect and Reptile research"
PATH = os.path.join(VAULT, "data", "isopods.json")
SRC = ["Hobby husbandry consensus — general care guideline; verify for your strain"]

# reusable substrate strings
TEMP_SUB = "Coco fiber / topsoil base, deep hardwood leaf litter, rotten wood, cuttlebone for calcium"
MED_SUB  = "Coco fiber / topsoil, leaf litter, rotten wood, limestone/cuttlebone; add ventilation"
ARID_SUB = "Topsoil + sand/limestone, leaf litter, cork/wood hides; strong cross-ventilation"
TROP_SUB = "Deep coco/topsoil, leaf litter, rotten wood, crushed limestone/oyster shell; keep humid"
MOIST_SUB = "Coco fiber + leaf litter kept consistently damp"

def H(common, size, origin, temp, hum, sub, diff, bio):
    return {"common_name": common, "adult_size_mm": size, "origin_region": origin,
            "temperature_c": temp, "humidity": hum, "substrate": sub,
            "difficulty": diff, "bioactive_use": bio, "sources": SRC}

# European care profiles (reused across many single-locality species)
def TEMPERATE(size, origin, bio, common="", diff="beginner"):
    return H(common, size, origin, "18-24", "Moderate; damp corner with good airflow", TEMP_SUB, diff, bio)
def MEDIT(size, origin, bio, common="", diff="beginner-intermediate"):
    return H(common, size, origin, "20-25", "Drier surface with a humid retreat; ventilated", MED_SUB, diff, bio)
def IBERIAN(size, origin, bio, common="", diff="intermediate"):
    return H(common, size, origin, "20-26", "Dry with a humid corner; strong ventilation", ARID_SUB, diff, bio)

# keyed by "Genus species" (described forms)
SPECIES = {
 "Armadillidium vulgare": H("Common pill bug (roly-poly)", "9-15 mm", "Europe (cosmopolitan)",
    "18-24", "Moderate; mostly-dry surface with one damp corner", TEMP_SUB, "beginner",
    "Excellent all-round cleanup crew; hardy, tolerates drier vivariums"),
 "Armadillidium maculatum": H("Zebra isopod", "12-18 mm", "SW Europe (S France)", "18-24",
    "Moderate; well cross-ventilated with a damp corner", MED_SUB, "beginner",
    "Popular display + cleanup; likes airflow and calcium"),
 "Armadillidium klugii": H("Klug's pill bug", "13-18 mm", "Balkans (Montenegro/Croatia)", "20-25",
    "Moderate with a humid retreat", MED_SUB, "beginner",
    "Display species; needs calcium and ventilation"),
 "Armadillidium gestroi": H("Marbled pill bug", "12-17 mm", "SW Europe", "20-25",
    "Moderate-high; humid corner", MED_SUB, "beginner-intermediate", "Colorful display species"),
 "Armadillidium nasatum": H("Nosy pill bug", "11-21 mm", "W Europe", "18-24",
    "Moderate; damp corner", TEMP_SUB, "beginner", "Good tolerant cleanup crew"),
 "Armadillidium espanyoli": H("", "9-12 mm", "Spain", "20-25",
    "Moderate; well ventilated", MED_SUB, "beginner", "Display + cleanup"),
 "Armadillo officinalis": H("Orange/Sicilian isopod", "18-22 mm", "Mediterranean", "22-26",
    "Moderate; deep substrate with a humid zone, strong ventilation", ARID_SUB, "intermediate",
    "Large display species; needs depth, calcium and airflow; can stridulate (buzz)"),

 "Porcellio scaber": H("Common rough woodlouse", "12-20 mm", "Europe (cosmopolitan)", "18-24",
    "Moderate; damp corner with good airflow", TEMP_SUB, "beginner",
    "Outstanding cleanup crew; hardy and prolific, many morphs"),
 "Porcellio laevis": H("Smooth / dairy-cow woodlouse", "15-20 mm", "Cosmopolitan", "20-25",
    "Moderate-high; fast growing", TEMP_SUB, "beginner",
    "Very fast, prolific cleanup crew and feeder; can outcompete slower species"),
 "Porcellio dilatatus": H("Giant Canyon isopod", "15-20 mm", "S Europe", "18-24",
    "Moderate; damp corner", TEMP_SUB, "beginner", "Robust cleanup crew"),
 "Porcellio hoffmannseggii": H("Giant Spanish isopod", "up to 30 mm", "Iberia / N Africa", "22-26",
    "Drier with a humid retreat; strong ventilation", ARID_SUB, "intermediate",
    "Large display species; needs warmth, calcium and ventilation"),
 "Porcellio magnificus": H("", "up to 30 mm", "SE Spain", "22-26",
    "Dry with a humid corner; ventilated", ARID_SUB, "intermediate", "Large striking display species"),
 "Porcellio ornatus": H("Ornate isopod", "15-25 mm", "Mediterranean / N Africa", "22-26",
    "Drier with a humid retreat", ARID_SUB, "intermediate", "Display species; several color forms"),
 "Porcellio expansus": H("", "18-28 mm", "S Spain", "22-26",
    "Dry with a humid corner", ARID_SUB, "intermediate", "Large display species"),
 "Porcellio bolivari": H("", "12-18 mm", "S Spain (caves)", "20-24",
    "Higher humidity than most Porcellio", MED_SUB, "intermediate", "Cave-associated display species"),
 "Porcellio wagneri": H("", "12-17 mm", "N Africa (Morocco)", "20-25",
    "Moderate; damp corner", MED_SUB, "beginner-intermediate", "Hardy display + cleanup"),

 "Porcellionides pruinosus": H("Powder blue isopod", "8-12 mm", "Cosmopolitan", "20-26",
    "Moderate; very tolerant", TEMP_SUB, "beginner",
    "Extremely fast and prolific feeder/cleanup colony; great starter and feeder species"),

 "Cubaris murina": H("Little Sea isopod", "8-12 mm", "SE Asia / pantropical", "22-26",
    "High (75-85%)", TROP_SUB, "intermediate", "Tropical cleanup; needs humidity and calcium"),
 "Trichorhina tomentosa": H("Dwarf white isopod", "3-5 mm", "Pantropical", "20-26",
    "High; keep consistently moist", MOIST_SUB, "beginner",
    "Premier micro cleanup crew for humid / dart-frog vivariums; parthenogenetic"),

 "Oniscus asellus": H("Common shiny woodlouse", "14-16 mm", "W/N Europe", "16-22",
    "Higher humidity; keep damp", TEMP_SUB, "beginner",
    "Good cleanup for humid temperate vivariums; prefers cooler, damp conditions"),
 "Philoscia muscorum": H("Common striped woodlouse", "6-11 mm", "Europe", "16-22",
    "Moderate; damp", TEMP_SUB, "beginner", "Fast, active temperate cleanup crew"),
 "Cylisticus convexus": H("Curly isopod", "10-15 mm", "Holarctic", "18-24",
    "Moderate; damp corner", TEMP_SUB, "beginner", "Hardy cleanup crew; a partial roller"),
 "Nagurus cristatus": H("Dwarf ridge isopod", "4-6 mm", "Pantropical", "20-26",
    "High; keep moist", MOIST_SUB, "beginner", "Micro cleanup crew"),
 "Trachelipus rathkii": H("Rathke's woodlouse", "10-15 mm", "Holarctic", "16-24",
    "Moderate; damp", TEMP_SUB, "beginner", "Temperate cleanup crew"),
 "Venezillo parvus": H("Dwarf pill isopod", "4-6 mm", "Pantropical", "22-26",
    "High", MOIST_SUB, "beginner-intermediate", "Tiny rolling cleanup crew for humid vivs"),
 "Atlantoscia floridana": H("Florida dwarf isopod", "3-5 mm", "Americas", "20-26",
    "Moderate-high", MOIST_SUB, "beginner", "Fast micro cleanup crew"),
 "Androniscus dentiger": H("Rosy woodlouse", "5-6 mm", "Europe", "16-22",
    "Damp", MOIST_SUB, "beginner", "Small damp-loving temperate species"),
 "Trichoniscus pusillus": H("Common pygmy woodlouse", "4-5 mm", "Europe", "14-20",
    "Damp; moisture-loving", MOIST_SUB, "beginner-intermediate", "Tiny moisture-dependent cleanup"),
 "Ligidium hypnorum": H("", "6-9 mm", "Europe", "14-20",
    "Very damp / riparian", MOIST_SUB, "intermediate", "Needs a consistently wet setup"),
 "Platyarthrus hoffmannseggii": H("Ant woodlouse", "3-4 mm", "Europe", "18-24",
    "Moderate; lives inside ant nests", MOIST_SUB, "advanced",
    "Obligate ant associate (myrmecophile); not a standalone cleanup crew"),
 "Niambia capensis": H("", "5-8 mm", "Africa", "20-26", "Moderate", MED_SUB, "beginner",
    "Hardy small cleanup crew"),
 "Hemilepistus reaumuri": H("Desert isopod", "up to 22 mm", "N Africa / Middle East deserts",
    "25-30 day, cooler night", "Very dry; deep burrows, minimal moisture",
    "Deep sand/clay, sparse leaf litter", "advanced",
    "Specialist social desert species; challenging, not a cleanup crew"),
 "Ligia oceanica": H("Sea slater", "up to 30 mm", "NE Atlantic coasts", "12-20",
    "Coastal splash zone; needs seawater/high humidity and ventilation", "Rock / brackish coastal",
    "advanced", "Specialist coastal species; not a terrarium cleanup crew"),
 "Ligia exotica": H("Sea roach / wharf louse", "up to 30 mm", "Warm coasts (introduced widely)",
    "18-26", "Coastal splash zone; brackish, high humidity, ventilated", "Rock / brackish coastal",
    "advanced", "Specialist coastal species; not a terrarium cleanup crew"),
 "Merulanella bicolorata": H("", "8-12 mm", "SE Asia", "22-26", "High (80%+)", TROP_SUB, "advanced",
    "Sensitive tropical display; stable humidity and calcium are critical"),

 # tropical / warm-climate described species (genus-level tropicals filled explicitly)
 "Nesodillo arcangelii": H("", "8-12 mm", "SE Asia", "22-26", "High (75-85%)", TROP_SUB, "intermediate",
    "Tropical rolling display species; humidity and calcium important"),
 "Troglodillo rotundatus": H("", "8-14 mm", "SE Asia", "22-26", "High (75-85%)", TROP_SUB, "intermediate",
    "Tropical rolling display species"),
 "Reductoniscus costulatus": H("", "3-5 mm", "Indo-Pacific (pantropical)", "22-26", "High; keep moist",
    TROP_SUB, "intermediate", "Tiny tropical rolling species; micro cleanup in humid vivariums"),
 "Pseudarmadillo spinosus": H("", "8-12 mm", "Caribbean", "22-26", "High", TROP_SUB, "intermediate-advanced",
    "Armored Caribbean display species; humidity and calcium critical"),
 "Spherillo danae": H("", "8-12 mm", "Australia", "22-26", "High", TROP_SUB, "intermediate",
    "Australian tropical/subtropical rolling display species"),
 "Nagurus nanus": H("Dwarf isopod", "3-5 mm", "Pantropical", "20-26", "High; keep moist", MOIST_SUB,
    "beginner", "Tiny tropical micro cleanup crew"),
 "Venezillo arizonicus": H("", "4-6 mm", "SW USA (Arizona)", "22-26",
    "Moderate-high; tolerates drier conditions than tropical Venezillo", MED_SUB, "beginner-intermediate",
    "Small warm-climate rolling species; more arid-tolerant than its tropical relatives"),

 # ---- temperate & Mediterranean European species ----
 "Armadillidium album": H("Coastal pillbug", "8-12 mm", "W European coasts", "18-24",
    "Moderate; coastal/sandy, ventilated", MED_SUB, "intermediate",
    "Coastal dune species; sandy substrate and airflow"),
 "Armadillidium arcangelii": MEDIT("9-13 mm", "Balkans", "Balkan pillbug species"),
 "Armadillidium badium": MEDIT("7-11 mm", "S/Central Europe", "Small European pillbug"),
 "Armadillidium decorum": MEDIT("10-14 mm", "S Europe / Mediterranean", "Mediterranean pillbug"),
 "Armadillidium depressum": TEMPERATE("9-14 mm", "W Europe", "Flat-backed European pillbug", common="Flat pillbug"),
 "Armadillidium granulatum": H("", "9-14 mm", "Mediterranean coasts", "20-25",
    "Moderate; coastal, ventilated", MED_SUB, "beginner-intermediate", "Coastal Mediterranean pillbug"),
 "Armadillidium peraccae": MEDIT("8-12 mm", "SW Europe", "SW European pillbug"),
 "Armadillidium pictum": H("Painted pillbug", "6-9 mm", "Central/E Europe (montane woodland)", "16-22",
    "Higher humidity; cool, damp woodland", TEMP_SUB, "intermediate",
    "Cool woodland species; legally protected in parts of Europe"),
 "Armadillidium versicolor": MEDIT("8-12 mm", "Central/SE Europe", "Variable European pillbug", diff="beginner"),
 "Armadillidium werneri": MEDIT("8-12 mm", "Greece / Balkans", "Balkan pillbug"),
 "Armadillo tuberculatus": H("", "12-18 mm", "Mediterranean", "22-26",
    "Drier with a humid retreat; ventilated", ARID_SUB, "intermediate",
    "Mediterranean roller; warmth, calcium and airflow"),
 "Agabiformius lentus": H("Persimmon isopod", "5-7 mm", "Mediterranean (warm cosmopolitan)", "20-26",
    "Moderate; tolerant", MED_SUB, "beginner", "Small hardy warm-climate cleanup crew"),
 "Buddelundiella cataractae": H("", "2-4 mm", "W/Central Europe", "16-22",
    "Damp; tiny cryptic species", MOIST_SUB, "intermediate", "Very small cryptic species; keep humid"),
 "Cristarmadillidium muricatum": H("Pinecone isopod", "8-12 mm", "Corsica & Sardinia", "20-25",
    "Moderate; ventilated with a humid retreat", MED_SUB, "intermediate", "Spiny Mediterranean display species"),
 "Eluma caelata": TEMPERATE("8-12 mm", "W European coasts", "Burrowing coastal woodlouse", diff="intermediate"),
 "Helleria brevicornis": H("", "up to 20 mm", "Tyrrhenian coasts (Corsica/Sardinia/Italy)", "18-24",
    "Moderate; deep sandy coastal soil, humid", "Sandy coastal soil with leaf litter", "intermediate",
    "Large primitive coastal species (Tylidae); a partial roller"),
 "Philoscia affinis": TEMPERATE("6-10 mm", "Europe", "Fast, active temperate woodlouse"),
 "Platyarthrus aiasensis": H("Ant woodlouse", "3-4 mm", "E Mediterranean", "18-24",
    "Moderate; lives inside ant nests", MOIST_SUB, "advanced",
    "Myrmecophile; obligate ant associate, not a standalone cleanup crew"),
 "Porcellionides myrmecophilus": H("", "6-9 mm", "Mediterranean", "20-26",
    "Moderate; often ant-associated", MED_SUB, "intermediate", "Fast Mediterranean species, frequently ant-associated"),
 "Porcellionides sexfasciatus": H("", "9-12 mm", "Mediterranean", "20-26",
    "Moderate; ventilated", MED_SUB, "beginner-intermediate", "Fast Mediterranean runner"),
 "Schizidium hybridum": IBERIAN("6-10 mm", "E Mediterranean / Middle East", "Roller from the arid E Mediterranean"),
 "Schizidium tiberianum": IBERIAN("6-10 mm", "E Mediterranean (Levant)", "Roller from the arid E Mediterranean"),
 "Porcellio albinus": H("", "8-12 mm", "Iberia (sand dunes)", "20-26",
    "Dry, sandy; strong ventilation with a humid corner", ARID_SUB, "intermediate",
    "Sand-dune specialist; needs sand and ventilation"),
 "Porcellio duboscqui": IBERIAN("10-14 mm", "N Africa / Iberia", "Iberian / N African woodlouse"),
 "Porcellio echinatus": IBERIAN("10-14 mm", "Iberia", "Iberian woodlouse"),
 "Porcellio flavomarginatus": IBERIAN("12-18 mm", "S Spain", "Large Iberian woodlouse"),
 "Porcellio gallicus": MEDIT("8-12 mm", "France / Iberia", "W Mediterranean woodlouse", diff="intermediate"),
 "Porcellio haasi": IBERIAN("12-18 mm", "SE Spain", "Large Iberian woodlouse"),
 "Porcellio incanus": IBERIAN("10-14 mm", "Mediterranean / Iberia", "Mediterranean woodlouse"),
 "Porcellio lamellatus": H("", "10-15 mm", "Mediterranean coasts", "20-25",
    "Coastal; sandy, ventilated", ARID_SUB, "intermediate", "Coastal sand species"),
 "Porcellio monticola": H("", "8-12 mm", "Iberian uplands", "18-24",
    "Moderate; damp corner", MED_SUB, "beginner-intermediate", "Upland Iberian woodlouse"),
 "Porcellio nicklesi": IBERIAN("10-14 mm", "N Africa", "N African woodlouse"),
 "Porcellio obsoletus": IBERIAN("10-16 mm", "Iberia / N Africa", "Large Iberian / N African woodlouse"),
 "Porcellio silvestrii": MEDIT("10-14 mm", "Italy", "Italian woodlouse", diff="intermediate"),
 "Porcellio spinicornis": H("Calcicole woodlouse", "10-15 mm", "Europe (calcareous walls)", "18-24",
    "Moderate; needs calcium (limestone/mortar)", MED_SUB, "beginner",
    "Calcicole; associated with limestone walls and mortar"),
 "Porcellio succinctus": IBERIAN("10-14 mm", "Iberia", "Iberian woodlouse"),
 "Porcellio werneri": MEDIT("12-16 mm", "Greece / Balkans", "Balkan woodlouse", diff="intermediate"),
}

# genus-level defaults for undescribed provisional sp. trade forms
GENUS = {
 "Cubaris": H("", "8-14 mm", "SE Asia", "22-26", "High (75-85%)", TROP_SUB, "intermediate-advanced",
    "Prized display species; humidity and calcium critical; often slower breeders"),
 "Merulanella": H("", "8-12 mm", "SE Asia", "22-26", "High (80%+); sensitive to swings", TROP_SUB,
    "advanced", "Delicate display; stable high humidity essential, boom-bust prone"),
 "Troglodillo": H("", "8-14 mm", "SE Asia", "22-26", "High", TROP_SUB, "intermediate",
    "Tropical rolling display species"),
 "Venezillo": H("", "4-8 mm", "Pantropical / Americas", "22-26", "High", TROP_SUB, "intermediate",
    "Small tropical rolling species"),
 "Nesodillo": H("", "8-12 mm", "SE Asia", "22-26", "High", TROP_SUB, "intermediate",
    "Tropical rolling display species"),
 "Tuberillo": H("", "6-12 mm", "Tropics", "22-26", "High", TROP_SUB, "intermediate-advanced",
    "Bumpy/spiny tropical display species"),
 "Trichorhina": H("", "3-5 mm", "Pantropical", "20-26", "High; keep moist", MOIST_SUB, "beginner",
    "Micro cleanup crew for humid vivariums"),
}

CARRY = ["adult_size_mm","origin_region","temperature_c","humidity","substrate",
         "difficulty","bioactive_use","sources"]

with open(PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
records = data["records"]
byid = {r["id"]: r for r in records}

filled = 0
for r in records:
    if r["record_type"] != "form":
        continue
    key = "%s %s" % (r["genus"], r["species"])
    h = None
    if r["is_described"] and key in SPECIES:
        h = SPECIES[key]
    elif not r["is_described"] and r["genus"] in GENUS:
        h = GENUS[r["genus"]]
    if h:
        for k, v in h.items():
            if k == "common_name" and not v:
                continue
            r[k] = v
        filled += 1

# morphs inherit the care fields of their parent form
morph_filled = 0
for r in records:
    if r["record_type"] != "morph":
        continue
    p = byid.get(r["parent_id"])
    if p and p.get("temperature_c"):
        for k in CARRY:
            r[k] = p.get(k, r.get(k, ""))
        morph_filled += 1

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1, ensure_ascii=False)

print("husbandry defaults filled: %d forms, %d morphs inherited." % (filled, morph_filled))
