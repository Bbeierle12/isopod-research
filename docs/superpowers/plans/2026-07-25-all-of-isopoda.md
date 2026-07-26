# All of Isopoda — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the vault from the terrestrial suborder Oniscidea (4,226 species) to the **entire order Isopoda** (~10,000 species across 11 suborders), restructured under a suborder layer, with the facet/research system extended to classify aquatic (marine & freshwater) taxa alongside terrestrial ones.

**Architecture:** Introduce an `Isopoda/<Suborder>/<Family>/<Genus>/<Species>.md` tree. Migrate the existing enriched Oniscidea notes intact under `Isopoda/Oniscidea/`. Crawl GBIF for the other 112 families and generate their notes. Add a curated `family → suborder → realm` map (GBIF has no suborder nodes). Add a **realm** axis (marine/brackish/freshwater/littoral/terrestrial) and extend the research-facet vocabularies (trophic guild, habitat stratum) for aquatic life. Husbandry/hobby facets stay Oniscidea-scoped.

**Tech Stack:** Python 3 (`urllib`, `json`, `re` — no third-party deps except optional `pypdf`/`pymupdf` already installed), GBIF Backbone Taxonomy REST API (`api.gbif.org`), Obsidian Markdown vault, git.

## Global Constraints

- **Taxonomy source:** GBIF Backbone Taxonomy only; order Isopoda `usageKey = 643`; families are direct `FAMILY` children of 643 (there are **154**). Restrict to `taxonomicStatus = ACCEPTED`.
- **Suborder classification source:** WoRMS (11 accepted suborders). GBIF has **no** suborder rank node, so family→suborder is a **curated map**, cited to WoRMS.
- **No fabricated names:** every species name comes from GBIF; never hand-type species. (Existing rule — see README.)
- **Preserve existing data:** the 4,226 Oniscidea notes carry hand/generated data (husbandry, `in_culture`, morphs, facets). Migration must not overwrite or drop any of it.
- **Idempotent generators:** every script re-runnable; content-identical on re-run (line-ending churn only, normalized by `.gitattributes`).
- **Link safety:** Obsidian resolves `[[Genus species]]` by basename; species basenames are globally unique, so moving files preserves links. Do not rename species notes.
- **Evidence grading:** research-axis values carry `a`=published / `b`=inferred-from-relatives / `c`=unstudied. Blank until researched; no family-level guessing on unstudied species (established convention).

---

## File Structure

**New/changed files:**

- Create `data/isopoda_suborders.json` — curated `family → {suborder, realm}` map for all 154 GBIF Isopoda families. The single source of truth for structure.
- Create `scripts/taxonomy.py` — GBIF crawler that builds the taxonomy tree for **non-Oniscidea** suborders under `Isopoda/<Suborder>/<Family>/<Genus>/<Species>.md`. Generalizes the original one-off Oniscidea build (which lived only in a scratchpad, never committed).
- Modify `scripts/generate.py:140` — `ONISCIDEA` constant → `Isopoda/Oniscidea`.
- Modify `scripts/atlas.py:18` — `ONISCIDEA` constant → `Isopoda/Oniscidea`; add the **realm** facet + aquatic vocabulary; scaffold research fields across the whole `Isopoda/` tree (not just Oniscidea).
- Modify `data/ecology.json` — extend the schema notes to allow `realm`, aquatic trophic/stratum values; no data churn required.
- Modify `Isopods.md`, `README.md`, and add `Isopoda/_Isopoda Index.md` (order-level master index).
- Moved (git mv, unchanged content): `Oniscidea/` → `Isopoda/Oniscidea/`.

**Realm is largely suborder-determined** (assign at suborder level, override per family only where a family is split across realms):

| Suborder | Default realm | Notes |
|---|---|---|
| Oniscidea | terrestrial | already in vault |
| Valvifera | marine | Idoteidae etc. |
| Sphaeromatidea | marine | + some estuarine |
| Cymothoida | marine | fish parasites (Cymothoidae), predators (Cirolanidae), Bopyridae |
| Limnoriidea | marine | wood/algae borers |
| Phoratopidea | marine | monotypic |
| Asellota | freshwater | + deep-sea marine (Munnopsidae etc.) — override those to marine |
| Phreatoicidea | freshwater | Gondwanan groundwater |
| Calabozoidea | freshwater | subterranean |
| Tainisopidea | freshwater | subterranean |
| Microcerberidea | interstitial (marine/fresh) | tiny psammic |

---

## Phase A — Structure & suborder map (non-destructive)

### Task A1: Build the family → suborder → realm map

**Files:**
- Create: `data/isopoda_suborders.json`
- Test: inline verification (below)

**Interfaces:**
- Produces: `data/isopoda_suborders.json` = `{"families": {"<Family>": {"suborder": "<Suborder>", "realm": "<realm>"}, ...}}` covering all 154 GBIF families.

- [ ] **Step 1: Fetch the authoritative family list from GBIF**

Run:
```bash
python - <<'PY'
import urllib.request, json
d=json.load(urllib.request.urlopen("https://api.gbif.org/v1/species/643/children?limit=300"))
fams=sorted(r['scientificName'] for r in d['results'] if r['rank']=='FAMILY')
print(len(fams)); print("\n".join(fams))
PY
```
Expected: `154` then the family names.

- [ ] **Step 2: Author `data/isopoda_suborders.json`**

Assign every family to one of the 11 WoRMS suborders and a realm. Start from the 42 Oniscidea families already curated in `scripts/husbandry.py`'s `ISOPOD_FAMILIES` set (all `suborder: Oniscidea, realm: terrestrial`). For the remaining 112, assign by WoRMS lookup; use the suborder-default realm table above, overriding per family where needed (e.g. deep-sea Asellota families → `marine`). Skip/flag any fossil-only family with `suborder: "incertae sedis"`.

Structure:
```json
{
  "_source": "Suborders per WoRMS; families per GBIF order Isopoda (usageKey 643), accessed 2026-07-25",
  "families": {
    "Oniscidae": {"suborder": "Oniscidea", "realm": "terrestrial"},
    "Idoteidae": {"suborder": "Valvifera", "realm": "marine"},
    "Cymothoidae": {"suborder": "Cymothoida", "realm": "marine"},
    "Cirolanidae": {"suborder": "Cymothoida", "realm": "marine"},
    "Bopyridae": {"suborder": "Cymothoida", "realm": "marine"},
    "Sphaeromatidae": {"suborder": "Sphaeromatidea", "realm": "marine"},
    "Limnoriidae": {"suborder": "Limnoriidea", "realm": "marine"},
    "Asellidae": {"suborder": "Asellota", "realm": "freshwater"},
    "Munnopsidae": {"suborder": "Asellota", "realm": "marine"},
    "Phreatoicidae": {"suborder": "Phreatoicidea", "realm": "freshwater"}
  }
}
```
(Add all 154 — the ten above are worked examples of the pattern.)

- [ ] **Step 3: Verify every GBIF family is mapped, with valid values**

Run:
```bash
python - <<'PY'
import urllib.request, json
gb=set(r['scientificName'] for r in json.load(urllib.request.urlopen("https://api.gbif.org/v1/species/643/children?limit=300"))['results'] if r['rank']=='FAMILY')
m=json.load(open(r"data/isopoda_suborders.json",encoding="utf-8"))["families"]
SUB={"Oniscidea","Valvifera","Sphaeromatidea","Cymothoida","Limnoriidea","Phoratopidea","Asellota","Phreatoicidea","Calabozoidea","Tainisopidea","Microcerberidea","incertae sedis"}
REALM={"terrestrial","marine","freshwater","brackish","littoral","interstitial"}
missing=gb-set(m); print("UNMAPPED families:", sorted(missing))
bad=[f for f,v in m.items() if v["suborder"] not in SUB or v["realm"] not in REALM]
print("BAD values:", bad)
assert not missing and not bad, "map incomplete/invalid"
print("OK:", len(m), "families mapped")
PY
```
Expected: `UNMAPPED families: []`, `BAD values: []`, `OK: 154 families mapped`.

- [ ] **Step 4: Commit**
```bash
git add data/isopoda_suborders.json
git commit -m "Add curated Isopoda family -> suborder -> realm map (154 families)"
```

---

## Phase B — Migrate the existing Oniscidea tree

### Task B1: Move Oniscidea under the new Isopoda/ root, intact

**Files:**
- Move: `Oniscidea/` → `Isopoda/Oniscidea/`
- Modify: `scripts/generate.py:140`, `scripts/atlas.py:18`

**Interfaces:**
- Produces: `Isopoda/Oniscidea/<Family>/<Genus>/<Species>.md` (all existing content preserved). `ONISCIDEA` path constant now points inside `Isopoda/`.

- [ ] **Step 1: Move the tree with git (preserves history + content)**
```bash
mkdir -p "Isopoda"
git mv "Oniscidea" "Isopoda/Oniscidea"
```

- [ ] **Step 2: Verify count unchanged and links still resolve by basename**
```bash
find "Isopoda/Oniscidea" -name '*.md' | wc -l   # expect 4835 (species + index notes, unchanged)
test ! -d "Oniscidea"                            # old path gone
```
Expected: `4835`, and the `test` returns success (exit 0).

- [ ] **Step 3: Update path constant in generate.py**

Modify `scripts/generate.py:140`:
```python
ONISCIDEA = os.path.join(VAULT, "Isopoda", "Oniscidea")
```

- [ ] **Step 4: Update path constant in atlas.py**

Modify `scripts/atlas.py:18`:
```python
ONISCIDEA = os.path.join(VAULT, "Isopoda", "Oniscidea")
```

- [ ] **Step 5: Re-run the pipeline; confirm it still resolves the moved notes (idempotent)**
```bash
python scripts/generate.py    # expect "enriched N Oniscidea taxonomy notes" with N>0, no errors
python scripts/atlas.py       # expect "Scaffolded research fields onto 4226 ... notes"
git -c core.whitespace=cr-at-eol diff --ignore-cr-at-eol --name-only | grep -v '^Isopoda/Oniscidea' | grep -vi warning
```
Expected: generate/atlas succeed with the same counts as before the move; the final diff shows only script/index files (no content change to species notes beyond the move).

- [ ] **Step 6: Commit**
```bash
git add -A
git commit -m "Migrate Oniscidea tree under Isopoda/; repoint pipeline path constants"
```

---

## Phase C — Crawl & generate the rest of Isopoda

### Task C1: Write the GBIF taxonomy crawler

**Files:**
- Create: `scripts/taxonomy.py`
- Test: inline verification (below)

**Interfaces:**
- Consumes: `data/isopoda_suborders.json` (Task A1).
- Produces: `Isopoda/<Suborder>/<Family>/<Genus>/<Species>.md` notes for every **non-Oniscidea** family; a per-species frontmatter template mirroring the Oniscidea species-note schema (`type: species`, `scientificName`, `authorship`, `genus`, `family`, `suborder`, `realm`, `gbif_id`, `gbif_url`, plus blank research-filter fields) and index notes (`_<Family> Index.md`, `_<Genus>.md`).

- [ ] **Step 1: Write `scripts/taxonomy.py`**

It must: load `isopoda_suborders.json`; for each family whose `suborder != "Oniscidea"`, resolve the family's GBIF key (via `/species/643/children`), page its `GENUS` children, then each genus's `SPECIES` children filtered to `taxonomicStatus == ACCEPTED`; write notes under `Isopoda/<safe(Suborder)>/<safe(Family)>/<safe(Genus)>/<safe(Genus species)>.md`. Reuse the proven crawl/paging/retry logic and `safe()` sanitiser from `scripts/generate.py`. Each species note frontmatter:
```
---
type: species
scientificName: <Genus species>
authorship: "<auth>"
genus: <Genus>
family: <Family>
suborder: <Suborder>
realm: <realm>
gbif_id: <id>
gbif_url: https://www.gbif.org/species/<id>
common_name:
distribution:
habitat:
ecomorph:
conglobation_type:
terrestrialization:
habitat_stratum:
trophic_guild:
reproduction_mode:
ecology_evidence:
sources:
status: stub
tags: [isopod, isopoda, <suborder-lower>, <family-lower>]
---

# <Genus species> <auth>

**Order** Isopoda › **Suborder** <Suborder> › **Family** [[_<Family> Index|<Family>]] › **Genus** [[_<Genus>|<Genus>]]

## Overview


## Distribution & habitat


## References
- GBIF: https://www.gbif.org/species/<id>
```
Print per-family progress (`[i/N] <Family> genera=.. species=..`) and a final total; write a progress log to the scratchpad so a long crawl is observable.

- [ ] **Step 2: Dry-run on ONE small marine family to validate output shape**

Temporarily restrict the family loop to `["Limnoriidae"]` (small family) and run:
```bash
python scripts/taxonomy.py
find "Isopoda/Limnoriidea/Limnoriidae" -name '*.md' | head
cat "Isopoda/Limnoriidea/Limnoriidae"/*/"Limnoria lignorum.md"  # spot-check a known species note
```
Expected: a `Limnoriidae` tree appears with real species notes carrying `realm: marine`, blank research fields, and a valid GBIF id.

- [ ] **Step 3: Remove the restriction; run the full crawl**
```bash
python scripts/taxonomy.py    # background if long; watch the scratchpad progress log
```
Expected: final line reports ~11 suborders, ~112 families, and on the order of 5,000–6,000 new accepted species (GBIF numbers vary; log the actual counts).

- [ ] **Step 4: Verify totals and that no Oniscidea notes were touched**
```bash
python - <<'PY'
import os
root=r"Isopoda"
subs=[d for d in os.listdir(root) if os.path.isdir(os.path.join(root,d))]
print("suborders:", sorted(subs))
tot=sum(len([f for f in fs if f.endswith('.md') and not f.startswith('_')]) for _,_,fs in os.walk(root))
print("total species notes across Isopoda:", tot)
PY
git status --short | grep '^ M "Isopoda/Oniscidea' | head   # expect NO modified Oniscidea notes
```
Expected: all 11 suborder folders present; total species notes ≈ 4,226 + new; **no** modified Oniscidea notes.

- [ ] **Step 5: Commit** (large add — expect thousands of files)
```bash
git add -A
git commit -m "Crawl & generate non-Oniscidea Isopoda taxonomy (11 suborders)"
```

---

## Phase D — Order-level indexes

### Task D1: Generate suborder/family indexes and the order master index

**Files:**
- Create: `Isopoda/_Isopoda Index.md`, and `_<Suborder> Index.md` inside each suborder folder.
- Modify: `scripts/taxonomy.py` (add an index-emitting pass), or add `scripts/isopoda_index.py`.

**Interfaces:**
- Produces: `Isopoda/_Isopoda Index.md` linking each suborder with family/genus/species counts + realm; each `_<Suborder> Index.md` linking its families.

- [ ] **Step 1: Add an index pass** that walks `Isopoda/`, counts species per suborder/family, and writes the index notes (mirror the existing `_Oniscidea Index.md` format: YAML frontmatter with counts + a Markdown table of links). Include a `realm` column at the suborder level.

- [ ] **Step 2: Verify the master index totals match the filesystem**
```bash
python - <<'PY'
import re
t=open(r"Isopoda/_Isopoda Index.md",encoding="utf-8").read()
print([l for l in t.splitlines() if "species_count" in l or "suborder_count" in l][:3])
PY
```
Expected: `suborder_count: 11` (or the mapped number) and a `species_count` equal to the Step-4 filesystem total from Task C1.

- [ ] **Step 3: Commit**
```bash
git add -A
git commit -m "Add Isopoda order + suborder index notes"
```

---

## Phase E — Extend the facet system for aquatic taxa

### Task E1: Add the realm axis and aquatic vocabularies to the Atlas

**Files:**
- Modify: `scripts/atlas.py`
- Modify: `data/ecology.json` (schema comment only; no data churn)

**Interfaces:**
- Consumes: `data/isopoda_suborders.json`, every species note's `realm`/`suborder` frontmatter.
- Produces: a `By Realm.md` facet map; research maps + scaffolding now span **all Isopoda** species; extended value orderings for `trophic_guild` and `habitat_stratum`.

- [ ] **Step 1: Broaden the taxonomy walk** in `atlas.py` from `ONISCIDEA` to the whole `Isopoda/` tree, so research fields scaffold onto every Isopoda species (blank until researched — unchanged rule).

- [ ] **Step 2: Add the `realm` facet.** Read `realm` from each species note (populated by the crawler / migration). Add a `By Realm.md` map with order `["terrestrial","littoral","brackish","freshwater","interstitial","marine"]`.

- [ ] **Step 3: Extend research-axis vocabularies** for aquatic life (used when `data/ecology.json` gains aquatic entries):
```python
# trophic_guild order (append aquatic guilds):
["General detritivore","Detritivore/coprophage","Detritivore (+herbivore)","Algivore/detritivore",
 "Wood-borer","Micropredator/scavenger","Parasite (ectoparasite)","Filter/deposit-feeder",
 "Detritivore (assumed/unstudied)"]
# habitat_stratum codes (append aquatic strata):
# EN EP CO AR CA LI SA MY  +  BE=benthic  PE=pelagic  IN=interstitial  WB=wood-boring  HA=host-associated  GW=groundwater
```
Ecomorph (Schmalfuss) is terrestrial-only — leave blank for non-Oniscidea; note this in the `By Ecomorph Type.md` subtitle.

- [ ] **Step 4: Run atlas; verify realm map + taxonomy-wide scaffold**
```bash
python scripts/atlas.py
sed -n '1,14p' "Maps/By Realm.md"
grep -c '^realm:' "Isopoda"/*/*/*/*.md | head   # realm present on notes
```
Expected: atlas reports scaffolding onto the full Isopoda species count; `By Realm.md` groups species by realm (terrestrial ≈ 4,226; marine/freshwater from the new crawl).

- [ ] **Step 5: Commit**
```bash
git add -A
git commit -m "Extend Atlas: realm axis + aquatic trophic/stratum vocab, span all Isopoda"
```

---

## Phase F — Wire up entry points & docs

### Task F1: Update MOC, README, memory

**Files:**
- Modify: `Isopods.md`, `README.md`

- [ ] **Step 1: Update `Isopods.md`** — retitle to the order; link `[[_Isopoda Index]]` as the top entry; keep the Oniscidea, Hobby, Atlas, Research links beneath.
- [ ] **Step 2: Update `README.md`** — change "Terrestrial Isopods (Oniscidea)" framing to "Order Isopoda"; update counts, the repo-layout table (`Isopoda/` replaces `Oniscidea/`), the `scripts/taxonomy.py` step in the pipeline, and the realm axis in the Atlas section. Keep GBIF/WoRMS attribution; add WoRMS as the suborder-classification source.
- [ ] **Step 3: Commit**
```bash
git add -A
git commit -m "Point entry points + README at order-wide Isopoda scope"
```

---

## Phase G — Verify, push, and health-check

### Task G1: Full-pipeline verification

- [ ] **Step 1: Run the whole pipeline end to end**
```bash
python scripts/taxonomy.py    # (idempotent: re-run should add nothing new)
python scripts/generate.py
python scripts/husbandry.py
python scripts/atlas.py
```
Expected: all succeed; the second `taxonomy.py` run reports 0 new species (idempotent).

- [ ] **Step 2: Content-idempotency check**
```bash
git add -A && python scripts/atlas.py >/dev/null
CH=$(git -c core.whitespace=cr-at-eol diff --ignore-cr-at-eol --name-only | grep -vi warning | wc -l)
echo "content changes on re-run: $CH (expect 0)"
```
Expected: `0`.

- [ ] **Step 3: Obsidian-scale note** — with ~13,000+ Markdown files the graph view gets heavy. Add `Maps/`, `data/`, `scripts/`, `docs/` are non-`.md` or few; no action required, but document in the README that graph view may be slow and Search/Bases are the intended navigation.

- [ ] **Step 4: Push**
```bash
git push origin main
```

---

## Risks & decisions

- **Family→suborder curation is the load-bearing manual step.** GBIF gives no suborder; a wrong assignment misfiles a whole family. Mitigation: cite WoRMS per family in `isopoda_suborders.json`; verify all 154 covered (Task A1 Step 3). Fossil/uncertain families → `incertae sedis` bucket, not force-fit.
- **Scale (~10k+ notes, ~13k+ files total).** Large git commits and a heavier Obsidian graph. Acceptable; navigation is via Search/indexes/Atlas, not the graph. The crawl is the long step — run in background with the progress log.
- **Aquatic biology doesn't fit terrestrial facets.** Ecomorph (Schmalfuss) and husbandry facets are terrestrial-only and stay blank for marine taxa — honest, not a gap to paper over. The **realm** axis and extended trophic/stratum vocab are the aquatic-appropriate filters.
- **GBIF marine synonym noise** is higher than for Oniscidea. The `ACCEPTED`-only filter (established) handles it; expect some genera with 0 accepted species (skip cleanly).
- **Migration data-loss risk.** The `git mv` preserves content and history; Task B1 Step 5 proves the pipeline still resolves the moved notes before anything else changes.

## Provenance

- Taxonomy: GBIF Backbone Taxonomy (`api.gbif.org`, order Isopoda `usageKey 643`), `ACCEPTED` only, accessed 2026-07-25.
- Higher classification (11 suborders, family placement): WoRMS World List of Isopods.
- License unchanged: MIT (`scripts/`) + CC BY 4.0 (data/content), GBIF attribution.

## Self-review

- **Spec coverage:** taxonomy pull (C1), suborder structure (A1/B1), realm + aquatic facets (E1), indexes (D1), docs (F1), verification (G1) — all covered.
- **Placeholders:** none — every step has exact paths, code, or commands with expected output. The 154-family map is authored in A1 with a worked pattern + a completeness gate rather than enumerated inline (enumeration is execution, gated by Step 3's assertion).
- **Consistency:** `ONISCIDEA` repoint (B1) matches the new `Isopoda/Oniscidea` path used everywhere; the species-note research fields written by `taxonomy.py` (C1) match the fields `atlas.py` scaffolds/reads (E1); realm values are the same set in A1, the crawler, and the `By Realm.md` order.
