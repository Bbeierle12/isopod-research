# -*- coding: utf-8 -*-
"""Enrich data/isopods.json in place against GBIF (idempotent).

Rules (conservative — never silently rewrite to a different species):
  * EXACT accepted match  -> gbif_id, authority, taxon_status=accepted.
  * EXACT synonym/doubtful -> keep the hobby's name, record accepted_name,
                              taxon_status=synonym|doubtful.
  * FUZZY match            -> apply ONLY as a spelling fix when edit-distance<=2
                              AND confidence>=95; otherwise taxon_status=needs_review
                              (keep original, record the GBIF suggestion).
  * no species match       -> taxon_status=unmatched.
Morph sub-records inherit the parent's corrected taxonomy. Ids are recomputed
from corrected names so the canonical file stays stable across runs."""
import os, json, re, urllib.request, urllib.parse, time

VAULT = r"C:\Users\Bbeie\Downloads\Insect and Reptile research"
PATH = os.path.join(VAULT, "data", "isopods.json")

ISOPOD_FAMILIES = {
 "Agnaridae","Alloniscidae","Armadillidae","Armadillidiidae","Balloniscidae","Bathytropidae",
 "Berytoniscidae","Bisilvestriidae","Brasileirinidae","Buddelundiellidae","Cylisticidae",
 "Delatorreiidae","Detonidae","Dubioniscidae","Eubelidae","Halophilosciidae","Ligiidae",
 "Mesoniscidae","Olibrinidae","Oniscidae","Paraplatyarthridae","Periscyphicidae","Philosciidae",
 "Platyarthridae","Porcellionidae","Pseudarmadillidae","Pudeoniscidae","Rhyscotidae",
 "Scleropactidae","Schoebliidae","Scyphacidae","Spelaeoniscidae","Sphaeroniscidae",
 "Stellatoniscidae","Stenoniscidae","Styloniscidae","Tendosphaeridae","Titanidae",
 "Trachelipodidae","Trichoniscidae","Turanoniscidae","Tylidae",
}

def slug(*parts):
    s = " ".join(p for p in parts if p)
    s = s.lower().replace("'", "").replace(".", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def lev(a, b):
    if a == b: return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (ca != cb)))
        prev = cur
    return prev[-1]

def gbif_match(genus, species):
    url = ("https://api.gbif.org/v1/species/match?strict=false&verbose=true&name="
           + urllib.parse.quote("%s %s" % (genus, species)))
    for _ in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(1.5)
    return {}

def is_isopod(m):
    return m.get("class") == "Malacostraca" or m.get("family") in ISOPOD_FAMILIES

with open(PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
records = data["records"]

corrections, id_remap = [], {}

for r in records:
    if r["record_type"] != "form" or not r["is_described"]:
        continue
    old_id = r["id"]
    r.pop("accepted_name", None); r.pop("gbif_suggestion", None)
    m = gbif_match(r["genus"], r["species"])
    mt, rank, status, conf = m.get("matchType"), m.get("rank"), m.get("status"), m.get("confidence", 0)
    canon = m.get("canonicalName", "")
    cparts = canon.split(" ", 1)
    c_genus = cparts[0] if cparts else r["genus"]
    c_epi = cparts[1] if len(cparts) > 1 else r["species"]
    good = rank == "SPECIES" and is_isopod(m) and mt in ("EXACT", "FUZZY")
    tight_fuzzy = mt == "EXACT" or (lev(r["species"], c_epi) <= 2 and conf >= 95)

    if good and tight_fuzzy:
        if (c_genus, c_epi) != (r["genus"], r["species"]):
            corrections.append("spelling: %s %s -> %s %s" % (r["genus"], r["species"], c_genus, c_epi))
        r["genus"], r["species"] = c_genus, c_epi
        r["gbif_id"] = m.get("usageKey")
        sci = m.get("scientificName", "")
        r["authority"] = sci.replace(canon, "").strip() if canon and canon in sci else ""
        if m.get("family") in ISOPOD_FAMILIES and m["family"] != r["family"]:
            corrections.append("family: %s %s -> %s" % (r["genus"], r["species"], m["family"]))
            r["family"] = m["family"]
        if status == "ACCEPTED":
            r["taxon_status"] = "accepted"
        elif status == "SYNONYM":
            r["taxon_status"] = "synonym"
            acc_sp = m.get("species", "")
            acc = acc_sp.strip() if " " in acc_sp else ("%s %s" % (m.get("genus", ""), acc_sp)).strip()
            if acc and acc != canon:
                r["accepted_name"] = acc
                corrections.append("synonym: %s = accepted %s" % (canon, acc))
        else:
            r["taxon_status"] = (status or "matched").lower()
    elif good and not tight_fuzzy:
        r["taxon_status"] = "needs_review"
        r["gbif_id"] = None
        r["gbif_suggestion"] = canon
        corrections.append("NEEDS REVIEW: %s %s ~ GBIF '%s' (conf %s) -> kept original"
                           % (r["genus"], r["species"], canon, conf))
    else:
        r["taxon_status"] = "unmatched"
        r["gbif_id"] = None
        corrections.append("UNMATCHED: %s %s (matchType=%s rank=%s)" % (r["genus"], r["species"], mt, rank))

    new_id = slug(r["genus"], r["species"])
    r["id"] = new_id
    if new_id != old_id:
        id_remap[old_id] = new_id

for r in records:  # provisional forms
    if r["record_type"] == "form" and not r["is_described"]:
        old_id = r["id"]; new_id = slug(r["genus"], "sp", r["trade_name"]); r["id"] = new_id
        if new_id != old_id: id_remap[old_id] = new_id

new_forms = {r["id"]: r for r in records if r["record_type"] == "form"}
for r in records:  # morphs inherit corrected parent
    if r["record_type"] != "morph": continue
    pid = id_remap.get(r["parent_id"], r["parent_id"]); r["parent_id"] = pid
    p = new_forms.get(pid)
    if p:
        r["family"], r["genus"], r["species"], r["gbif_id"] = p["family"], p["genus"], p["species"], p.get("gbif_id")
    r["id"] = pid + "--" + slug(r["morph_name"])

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1, ensure_ascii=False)

from collections import Counter
st = Counter(r["taxon_status"] for r in records if r["record_type"] == "form" and r["is_described"])
print("validated %d described forms | status:" % sum(st.values()), dict(st))
print("\nCorrections / flags (%d):" % len(corrections))
for c in corrections: print("  ", c)
