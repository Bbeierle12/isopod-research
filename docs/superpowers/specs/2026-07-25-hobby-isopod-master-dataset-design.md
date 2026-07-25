# Hobbyist Isopod Master Dataset — Design

**Date:** 2026-07-25
**Status:** Approved
**Repo:** github.com/Bbeierle12/isopod-research (Obsidian vault)

## Problem

Formal *Oniscidea* taxonomy and hobby nomenclature follow different rules. The
existing `Oniscidea/` tree is a pure GBIF-sourced scientific taxonomy (42 families,
567 genera, 4,226 accepted species). It cannot represent the hobby's reality:

- **Undescribed forms** — Southeast-Asian imports sold as *Cubaris* sp. "Rubber Ducky",
  *Merulanella* sp. "Ember Bee", etc. Have no scientific name, so no place in a
  Family→Genus→Species tree.
- **Localities** — wild collection strains (e.g. *A. klugii* "Montenegro").
- **Cultivars / morphs** — selectively bred lines (e.g. *P. scaber* "Koi").

A master dataset must keep biological classification separate from trade names,
localities, and cultivars, while linking them.

## Decisions (approved)

1. **Source of truth: hybrid.** A canonical structured data file owns the catalog
   (taxonomy + hobby nomenclature). Generated notes own free-text husbandry that the
   generator never overwrites.
2. **Grain: two-tier.** Species/sp. is the primary `form` record; each significant
   morph/cultivar is a lightweight `morph` sub-record that inherits its parent and
   stores only what differs.
3. **Placement: separate `Hobby/` tree** that links into the pure `Oniscidea/`
   taxonomy. The scientific tree stays untouched.
4. **Format:** JSON canonical (nests two-tier records naturally) + generated CSV
   export. **IDs:** deterministic slugs (not random UUIDs) so regeneration is stable.

## Architecture

```
data/isopods.json  ── canonical catalog (human + tool edited, git-tracked)
   │
   ├─ scripts/validate.py  → match is_described records to GBIF; correct spellings;
   │                          set gbif_id / taxon_status / authority; flag mismatches.
   │                          Enriches isopods.json in place (idempotent).
   │
   └─ scripts/generate.py  → idempotent frontmatter upsert into Hobby/ notes
                             (husbandry prose untouched); build _Hobby Catalog.md;
                             export data/isopods.csv
Outputs:
  Hobby/<Genus>/<Form>.md               form record note
  Hobby/<Genus>/<Form> — <Morph>.md     morph sub-record note
  Hobby/_Hobby Catalog.md               generated master index/table
  data/isopods.csv                      flat "database" export
```

JSON is the source of truth; notes and CSV are regenerable views.

## Schema (per record)

| Field | Type | Notes |
|---|---|---|
| `id` | slug | `armadillidium-vulgare--magic-potion`; stable/deterministic |
| `record_type` | enum | `form` \| `morph` |
| `family` | string | taxonomic family |
| `genus` | string | genus (validated where described) |
| `species` | string | epithet, or `sp.` for undescribed |
| `is_described` | bool | `false` for provisional/undescribed trade forms |
| `gbif_id` | int/null | filled by validate.py for described records |
| `taxon_status` | enum | `accepted` \| `synonym` \| `unmatched` \| `provisional` |
| `authority` | string | author, year (from GBIF) |
| `trade_name` | string | market identifier (e.g. "Rubber Ducky") |
| `locality` | string | wild origin / geographic strain |
| `morph_name` | string | cultivar / selected line (morph records) |
| `parent_id` | slug/null | morph → its form record |
| `conglobation` | enum | `FULL` \| `PARTIAL` \| `NONE`; defaulted per genus, overridable |
| `adult_size_mm` | string | size range |
| `origin_region` | string | native range |
| `temperature_c` | string | catalog default |
| `humidity` | string | catalog default |
| `substrate` | string | catalog default |
| `difficulty` | enum | beginner \| intermediate \| advanced |
| `bioactive_use` | string | cleanup-crew suitability |
| `sources` | list | citations |
| `verified_on` | date | last GBIF verification |

## Taxonomy verification

Every `is_described: true` record is matched to GBIF at build time. Fuzzy matches
correct known spelling traps (`nickelsi`→`nicklesi`, `arizoniscus`→`arizonicus`);
genus/epithet confusions are surfaced via `taxon_status`. Undescribed forms are
explicitly `is_described: false`, `taxon_status: provisional`, `gbif_id: null`.
Known corrections captured during design:

- `Porcellio nickelsi` → **nicklesi** (Dollfus, 1892)
- `Venezillo arizoniscus` → **arizonicus** (Mulaik & Mulaik, 1942)
- hobby *Venezillo* "arcangelii" → **Nesodillo arcangelii** (distinct from
  *Armadillidium arcangelii*, same epithet, different animal)
- "Tuberillidae" is not a family; *Tuberillo* is in **Armadillidae**
- Hobby-only genera with no GBIF record: **Ardentiella, Filipinodillo, Laureola**

## Seed scope

Seed from the approved genus breakdown: ~40 genera, ~120–160 `form` records
(described species + undescribed sp. trade forms), plus notable morphs as `morph`
sub-records. Described names corrected via validate.py; undescribed forms flagged
provisional.

## Non-goals

- No change to the existing `Oniscidea/` scientific tree (its 76 `in_culture` flags
  remain the taxonomy-side cross-reference).
- No per-morph husbandry prose auto-authored — the generator seeds frontmatter only.
- No live marketplace pricing/inventory.

## Verification resources

WoRMS (World List of Isopods) — authoritative names/synonyms; AIMG — traded-species
checklists; GBIF/iNaturalist — locality/range and machine verification.
