# -*- coding: utf-8 -*-
"""One-time bootstrap: build data/isopods.json from the approved genus breakdown.
After this runs, data/isopods.json is the canonical hand-edited file; validate.py
enriches it and generate.py builds views. Re-running seed overwrites — only for
initial population or a deliberate reseed."""
import os, json, re

VAULT = r"C:\Users\Bbeie\Downloads\Insect and Reptile research"
OUT = os.path.join(VAULT, "data", "isopods.json")

FULL, PARTIAL, NONE = "FULL", "PARTIAL", "NONE"

# genus -> (family_hint, conglobation, described{epithet: {morphs, localities}}, sp_forms[trade_name])
# family_hint is a starting guess; validate.py confirms/corrects described records against GBIF.
G = {
 # ---- Armadillidiidae (rollers) ----
 "Armadillidium": ("Armadillidiidae", FULL, {
    "vulgare": {"morphs": ["Magic Potion","Punto Rojo","Orange Vigor","St. Lucia","High White"]},
    "maculatum": {}, "klugii": {"localities": ["Montenegro","Dubrovnik"]},
    "gestroi": {}, "granulatum": {}, "werneri": {}, "peraccae": {}, "depressum": {},
    "badium": {}, "nasatum": {"morphs": ["Peach"]}, "espanyoli": {"morphs": ["Marbleize"]},
    "arcangelii": {}, "frontirostre": {}, "pictum": {}, "versicolor": {},
    "decorum": {}, "album": {},
 }, []),
 "Cristarmadillidium": ("Armadillidiidae", FULL, {"muricatum": {"morphs": ["Pinecone / Spiny"]}}, []),
 "Paxodillidium": ("Armadillidiidae", FULL, {"schmalfussi": {}}, []),
 "Schizidium": ("Armadillidiidae", FULL, {"tiberianum": {}, "hybridum": {}}, []),
 "Eluma": ("Armadillidiidae", FULL, {"caelata": {}}, []),

 # ---- Armadillidae (tropical/mediterranean rollers) ----
 "Cubaris": ("Armadillidae", FULL, {"murina": {}},
    ["Rubber Ducky","Panda King","Pak Chong","Jupiter","Cappuccino","Amber Firefly","Penguin","Blue Pigeon"]),
 "Armadillo": ("Armadillidae", FULL, {"officinalis": {"localities": ["Sicily","Spain"]}, "tuberculatus": {}}, []),
 "Troglodillo": ("Armadillidae", FULL, {"rotundatus": {}}, ["Soil","Green Spots"]),
 "Venezillo": ("Armadillidae", FULL, {"parvus": {}, "arizoniscus": {}}, ["Tank","Maya"]),
 "Nesodillo": ("Armadillidae", FULL, {"arcangelii": {"morphs": ["Shiro Utsuri"]}}, []),
 "Merulanella": ("Armadillidae", FULL, {"bicolorata": {}},
    ["Yellow Panda","Ember Bee","Scarlet","Red Diablo","Tricolor"]),
 "Dryadillo": ("Armadillidae", FULL, {}, ["Feather"]),
 "Filipinodillo": ("Armadillidae", FULL, {}, ["sp."]),
 "Laureola": ("Armadillidae", FULL, {}, ["Arboreal Spiny"]),
 "Reductoniscus": ("Armadillidae", FULL, {"costulatus": {}}, []),
 "Spherillo": ("Armadillidae", FULL, {"danae": {}}, []),
 "Tuberillo": ("Armadillidae", FULL, {}, ["Spiny Hedgehog","Bumpy"]),

 # ---- Scleropactidae ----
 "Adinda": ("Scleropactidae", FULL, {}, ["Grizzly Bear"]),

 # ---- Delatorreiidae ----
 "Pseudarmadillo": ("Delatorreiidae", FULL, {"spinosus": {"morphs": ["Caribbean Armored"]}}, []),

 # ---- Porcellionidae (non-rolling runners) ----
 "Porcellio": ("Porcellionidae", NONE, {
    "scaber": {"morphs": ["Dalmatian","Orange","Koi","Piebald","Ghost","Lava","Spanish Orange"]},
    "laevis": {"morphs": ["Dairy Cow","Orange","White","Milkback"]},
    "dilatatus": {}, "hoffmannseggi": {}, "werneri": {}, "magnificus": {}, "haasi": {},
    "ornatus": {"morphs": ["High Yellow","Yellow Ducky","South"]},
    "expansus": {"morphs": ["Yellow","Orange"]}, "nickelsi": {}, "spatulatus": {},
    "spinicornis": {}, "incanus": {}, "echinatus": {}, "lamellatus": {}, "wagneri": {},
    "bolivari": {}, "sevilla": {}, "albinus": {}, "gallicus": {}, "obsoletus": {},
    "monticola": {}, "silvestrii": {}, "succinctus": {}, "flavomarginatus": {}, "duboscqui": {},
 }, []),
 "Porcellionides": ("Porcellionidae", NONE, {
    "pruinosus": {"morphs": ["Powder Blue","Powder Orange","White Out"]},
    "floria": {}, "myrmecophilus": {}, "sexfasciatus": {},
 }, []),
 "Agabiformius": ("Porcellionidae", NONE, {"lentus": {"morphs": ["Persimmon"]}}, []),

 # ---- Cylisticidae (partial rollers) ----
 "Cylisticus": ("Cylisticidae", PARTIAL, {"convexus": {}}, []),

 # ---- Oniscidae / Philosciidae ----
 "Oniscus": ("Oniscidae", NONE, {"asellus": {"morphs": ["Mardi Gras","Dwarf","BC Maple"]}}, []),
 "Philoscia": ("Philosciidae", NONE, {"muscorum": {}, "affinis": {}}, []),
 "Atlantoscia": ("Philosciidae", NONE, {"floridana": {}}, []),

 # ---- Trachelipodidae ----
 "Trachelipus": ("Trachelipodidae", NONE, {"rathkii": {}, "squamatus": {}}, []),
 "Nagurus": ("Trachelipodidae", NONE, {"cristatus": {}, "nanus": {}}, []),

 # ---- Platyarthridae ----
 "Trichorhina": ("Platyarthridae", NONE, {"tomentosa": {}}, ["Dwarf Purple"]),
 "Platyarthrus": ("Platyarthridae", NONE, {"hoffmannseggii": {}, "aiasensis": {}}, []),
 "Niambia": ("Platyarthridae", NONE, {"capensis": {}}, []),

 # ---- Trichoniscidae ----
 "Androniscus": ("Trichoniscidae", NONE, {"dentiger": {"morphs": ["Rosy"]}}, []),
 "Trichoniscus": ("Trichoniscidae", NONE, {"pusillus": {}}, []),
 "Buddelundiella": ("Trichoniscidae", NONE, {"cataractae": {}}, []),

 # ---- Agnaridae ----
 "Hemilepistus": ("Agnaridae", NONE, {"reaumuri": {}, "elongatus": {}}, []),

 # ---- Ligiidae ----
 "Ligia": ("Ligiidae", NONE, {"exotica": {}, "oceanica": {}}, []),
 "Ligidium": ("Ligiidae", NONE, {"hypnorum": {}}, []),

 # ---- Tylidae (coastal) ----
 "Tylos": ("Tylidae", FULL, {"punctatus": {}}, []),
 "Helleria": ("Tylidae", PARTIAL, {"brevicornis": {}}, []),

 # ---- Detonidae ----
 "Deto": ("Detonidae", NONE, {"echinata": {}}, []),
}

def slug(*parts):
    s = " ".join(p for p in parts if p)
    s = s.lower().replace("'", "").replace(".", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s

records = []

def blank_husbandry():
    return {"adult_size_mm": "", "origin_region": "", "temperature_c": "",
            "humidity": "", "substrate": "", "difficulty": "", "bioactive_use": ""}

for genus, (fam, cong, described, sp_forms) in G.items():
    # described species -> form records
    for epi, meta in described.items():
        fid = slug(genus, epi)
        rec = {"id": fid, "record_type": "form", "family": fam, "genus": genus,
               "species": epi, "is_described": True, "gbif_id": None,
               "taxon_status": "unverified", "authority": "",
               "trade_name": "", "locality": "", "morph_name": "", "parent_id": None,
               "conglobation": cong}
        rec.update(blank_husbandry())
        rec["sources"] = []; rec["verified_on"] = ""
        records.append(rec)
        # localities as trait note on the form (kept as list field)
        rec["localities"] = meta.get("localities", [])
        # morphs -> morph sub-records
        for m in meta.get("morphs", []):
            mid = fid + "--" + slug(m)
            mr = {"id": mid, "record_type": "morph", "family": fam, "genus": genus,
                  "species": epi, "is_described": True, "gbif_id": None,
                  "taxon_status": "inherit", "authority": "",
                  "trade_name": "", "locality": "", "morph_name": m, "parent_id": fid,
                  "conglobation": cong}
            mr.update(blank_husbandry())
            mr["sources"] = []; mr["verified_on"] = ""
            records.append(mr)
    # undescribed sp. trade forms -> form records (is_described False)
    for tn in sp_forms:
        fid = slug(genus, "sp", tn)
        rec = {"id": fid, "record_type": "form", "family": fam, "genus": genus,
               "species": "sp.", "is_described": False, "gbif_id": None,
               "taxon_status": "provisional", "authority": "",
               "trade_name": tn, "locality": "", "morph_name": "", "parent_id": None,
               "conglobation": cong}
        rec.update(blank_husbandry())
        rec["sources"] = []; rec["verified_on"] = ""
        rec["localities"] = []
        records.append(rec)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"schema_version": 1, "records": records}, f, indent=1, ensure_ascii=False)

forms = [r for r in records if r["record_type"] == "form"]
morphs = [r for r in records if r["record_type"] == "morph"]
undesc = [r for r in forms if not r["is_described"]]
print("seeded %d records: %d forms (%d described, %d provisional sp.), %d morphs, %d genera"
      % (len(records), len(forms), len(forms)-len(undesc), len(undesc), len(morphs), len(G)))
