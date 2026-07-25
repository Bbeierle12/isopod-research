# Insect & Reptile Research — Isopod Vault

An [Obsidian](https://obsidian.md) vault and open dataset for **terrestrial isopod (Oniscidea)**
research and the bioactive-terrarium keeping hobby. It pairs a full GBIF-derived scientific
taxonomy with a structured, husbandry-annotated catalog of the species and morphs kept in the
hobby, plus a cited research layer.

> [!important] What this is and isn't
> This is a **working research vault and hobby dataset**, not a taxonomic authority. Scientific
> names come from GBIF; husbandry values are **hobby-consensus guidance**, not per-strain
> measurements; and ecology facts carry an explicit **evidence grade** (see below). Verify against
> [WoRMS](https://www.marinespecies.org/) and primary literature before relying on any record.

## Repository layout

| Path | What it is |
|---|---|
| `Isopods.md` | Entry point / map of content |
| `Oniscidea/` | Scientific taxonomy — family → genus → species notes (GBIF) |
| `Hobby/` | Undescribed `sp.` trade forms + morph cultivars; `_Hobby Catalog.md` |
| `data/isopods.json` · `.csv` | Canonical hobby catalog (source of truth) + flat export |
| `scripts/` | Idempotent pipeline that builds the notes/catalog/CSV |
| `Research/` | Categorization outline, per-species ecology data, source PDFs |
| `docs/superpowers/specs/` | Design spec for the master dataset |

## Scientific taxonomy (`Oniscidea/`)

**42 families · 567 genera · 4,226 accepted species** — one folder per family → genus → species.
Taxonomy was pulled from the **GBIF Backbone Taxonomy** (`api.gbif.org`) on **2026-07-24**,
restricted to `taxonomicStatus = ACCEPTED` (synonyms/doubtful/unranked excluded). Every species
note carries its GBIF id and URL. Start at [`Isopods.md`](Isopods.md).

## Hobby master dataset

`data/isopods.json` is the canonical, structured catalog of **hobby-relevant** isopods — described
species, undescribed `sp.` trade forms, and morph cultivars — kept separate from the scientific
taxonomy (design: `docs/superpowers/specs/2026-07-25-hobby-isopod-master-dataset-design.md`).

Pipeline (idempotent — re-running changes nothing unless inputs change):

```
python scripts/seed.py       # one-time bootstrap of data/isopods.json
python scripts/validate.py   # verify described records against GBIF (in place)
python scripts/husbandry.py  # set husbandry DEFAULTS (in place)
python scripts/generate.py   # build Hobby/ notes, _Hobby Catalog.md, data/isopods.csv
```

**Described species are consolidated onto their `Oniscidea/` scientific note** (`generate.py`
enriches each with husbandry, `conglobation`, `bioactive_use`, fill-if-empty so hand edits always
win); `Hobby/` holds only undescribed trade forms + morphs. Browse
[`Hobby/_Hobby Catalog.md`](Hobby/_Hobby%20Catalog.md).

Currently **112 forms** (88 described + 24 provisional) + **34 morphs** across 40 genera, with
husbandry defaults on all 146 records.

## Research layer (`Research/`)

- **`Isopod Categorization & Research Outline.md`** — 13 categorization axes (taxonomy,
  ecomorphology, terrestrialization, habitat stratum, biogeography, trophic guild, life-history,
  applied/hobby, …) + 8 research methodologies, verified against external sources.
- **`Isopod Species Ecology Data.md`** — per-species habitat-stratum / trophic-guild / life-history
  tables for ~40 taxa.
- `Research/sources/` — source documents.

> [!note] Evidence grading
> Ecology data is graded: **a** = published fact · **b** = inference from close relatives ·
> **c** = genuinely unstudied. Trade-name *Cubaris*/*Merulanella* and several tropical taxa are
> **b/c** — husbandry-sourced. This convention is deliberate: inference must never harden into fact.

## Data sources & attribution

- **Taxonomy:** [GBIF Backbone Taxonomy](https://www.gbif.org/) — GBIF Secretariat, licensed
  **CC BY 4.0**. This dataset is a derivative and attributes GBIF accordingly.
- **Nomenclature reference:** [WoRMS](https://www.marinespecies.org/) World List of Isopods.
- **Husbandry & trade data:** hobby-community consensus (general care guidance; verify for your strain).

## License

Dual-licensed — see [`LICENSE`](LICENSE):

- **Data & written content** (notes, `data/`, `Research/`, taxonomy compilation): **CC BY 4.0**.
- **Source code** (`scripts/`): **MIT**.

Attribution: *Bbeierle12 / isopod-research*, and **GBIF** for the underlying taxonomy.
