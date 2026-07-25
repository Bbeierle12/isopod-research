# Insect & Reptile Research

An [Obsidian](https://obsidian.md) vault for insect and reptile keeping / bioactive research.

## Terrestrial Isopods (Oniscidea)

The `Oniscidea/` section is a full taxonomic scaffold of the terrestrial isopods —
woodlice, pillbugs, sowbugs, and relatives.

- **42 families · 567 genera · 4,226 accepted species**
- One folder per family → one folder per genus → one note per species
- Index notes at every level (`_Oniscidea Index.md`, `_<Family> Index.md`, `_<Genus>.md`)
- Start at [`Isopods.md`](Isopods.md) or `Oniscidea/_Oniscidea Index.md`

### Data provenance

Taxonomy was pulled from the **GBIF Backbone Taxonomy** (`api.gbif.org`) on **2026-07-24**,
restricted to names with `taxonomicStatus = ACCEPTED`. Synonyms, doubtful, and unranked
names were excluded. Every species note carries its GBIF id and URL — cross-check against
[WoRMS](https://www.marinespecies.org/) or primary literature before relying on any record.

Species notes are stubs (`status: stub`) with blank husbandry frontmatter fields
(`common_name`, `distribution`, `habitat`, `size_mm`, `temperature_c`, `humidity`,
`substrate`, `diet`, `in_culture`, `morphs`, `difficulty`, `sources`) ready to fill in.

> **Note:** add new species by pulling accepted names from GBIF/WoRMS rather than typing
> them from memory, to keep the dataset free of fabricated names.

## Hobby Master Dataset

`data/isopods.json` is the canonical, structured catalog of **hobby-relevant** isopods —
described species, undescribed `sp.` trade forms, and morph cultivars — kept separate from
the scientific taxonomy above (see `docs/superpowers/specs/2026-07-25-hobby-isopod-master-dataset-design.md`).

Pipeline (idempotent):

```
python scripts/seed.py       # one-time bootstrap of data/isopods.json
python scripts/validate.py   # verify described records against GBIF (in place)
python scripts/husbandry.py  # set husbandry DEFAULTS for well-documented forms (in place)
python scripts/generate.py   # build Hobby/ notes, _Hobby Catalog.md, data/isopods.csv
```

**Described species are consolidated onto their scientific note** in `Oniscidea/` — `generate.py`
enriches each with husbandry, `conglobation`, and `bioactive_use` (fill-if-empty, so a value you
type always wins and note prose is never touched). `Hobby/` therefore holds only the **undescribed
`sp.` trade forms and morph cultivars** (which have no taxonomy note), avoiding duplicate/ambiguous
notes. The full picture is the generated index [`Hobby/_Hobby Catalog.md`](Hobby/_Hobby%20Catalog.md),
which links described species to their `Oniscidea/` note and lists the trade forms + morphs.

Currently 112 forms (88 described, 24 provisional) + 34 morphs across 40 genera; husbandry defaults
populated for 55 well-documented forms (the rest intentionally left blank).
