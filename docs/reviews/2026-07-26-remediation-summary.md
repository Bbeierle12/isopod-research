# Remediation summary — what the reviews found and what was fixed

This closes the loop on the five review documents in this folder. Every fix was
verified against the vault on disk and, for the biology, against the live WoRMS
and GBIF APIs. Commits are on `claude/isopod-vault-expansion-review-g3shid`.

## Pipeline correctness (from the code review)

| Finding | Status | Where |
|---|---|---|
| `taxonomy.py` didn't compile on Python ≤3.11 (f-string backslash) | **Fixed** | rewritten; `json.dumps` authorship; 3.9+ floor |
| 14,530 broken wikilinks (family/genus index notes never generated) | **Fixed** | `isopoda_index.py` now emits them; re-audit shows **0 broken links** |
| `atlas.py` unescaped `re.sub` replacement (crash on `\`) | **Fixed** | shared `_vault.set_field` uses a function replacement |
| `atlas.py` `^key:.*$` folds multi-line YAML values into scalars | **Fixed** | `_vault` refuses to rewrite block values |
| `atlas.py` `quote()` emits invalid YAML | **Fixed** | replaced by `_vault.emit_val` (round-trips through a YAML parser) |
| Crawler: 1,138 sequential `/children` calls, silent truncation | **Fixed** | `/species/search` (~12 requests), raises on failure, reports unplaced species |
| `VAULT` hardcoded in 7 scripts; `seed.py` path stale | **Fixed** | all derive from `_vault.VAULT` (env override) |
| Non-idempotent date churn; wrong counts | **Fixed** | `write_if_changed`; counts from disk |
| `atlas.py` `built[8:]` magic slice; realm regex crosses newline; non-atomic writes; no `main()` | **Fixed** | explicit groups; frontmatter-only regex; atomic temp+rename; `main()` + `--dry-run` |

## Classification accuracy (from the audit) — verified against WoRMS

| Finding | Status | Detail |
|---|---|---|
| Suborder **Epicaridea** missing; 891 notes misplaced | **Fixed** | 17 families moved out of Cymothoida/Oniscidea into Epicaridea |
| **Stellatoniscidae** (marine parasite) in Oniscidea/terrestrial | **Fixed** | → Epicaridea / marine |
| 12 family realms contradict WoRMS (216 notes) | **Fixed** | 8 marine asellotes relabelled; Lepidocharontidae/Microparasellidae un-swapped |
| `norm_repro` files sexual species as Parthenogenetic | **Fixed** | negation/hedge guarded; only the 2 genuinely parthenogenetic taxa remain |
| `incertae sedis` = fossil dump with guessed `realm: marine`; no `extinct` flag | **Fixed** | 6 fossil families flagged `extinct`; Palaeophreatoicidae → Phreatoicidea/freshwater |
| 6 misspelling-duplicate families + junior synonyms | **Fixed** | 7 phantoms removed; `Amphisopodidae`→`Amphisopidae` (Lakeamphisopus rehomed) |
| `_Asellota Index` "Realm: marine" for a mixed suborder | **Fixed** | suborder realm is now the union of its families |
| Single-valued realm can't express Ligiidae etc. | **Fixed (data)** | `realms[]` (WoRMS environment set) added to the family map |

Deliberately **not** changed: the Epicaridea-vs-Cymothoida placement is a real
taxonomic choice; it was resolved toward **WoRMS**, which the map's `_source`
already cited. If you prefer Brandt & Poore (2003) (Epicaridea *within*
Cymothoida), revert the suborder moves — the decision is now explicit, not
accidental.

## Matrix compliance + external-review reconciliation

| Finding | Status | Detail |
|---|---|---|
| Open nomenclature (`species: "sp."`) in 24 forms — the I.4 HARD FAIL | **Fixed** | moved to `open_nomenclature`; 0 tokens remain in any species field |
| `authorship` not atomized | **Fixed (tooling)** | `build_db.py` splits author/year/`is_reassigned`; `schema.sql` stores them apart |
| No taxonomic-status field / no WoRMS id / no References table | **Addressed** | `schema.sql` adds the status enum, `worms_aphia_id`, and a normalized `reference_source` table; family AphiaIDs recorded in the map |
| The four `schema.sql` defects (no open-nom column; free-text source; overloaded parent; NULL-authority leak) | **Fixed** | corrected `data/schema.sql`; proven loadable by `build_db.py` |

## Verification (re-run any of these)

```
python scripts/build_db.py        # 0 CHECK violations, 0 collisions across 11,435 species
python scripts/atlas.py --dry-run # "33 studied" (was the bogus 11,448)
python scripts/isopoda_index.py   # regenerates indexes; broken-link audit -> 0
```

- **0** broken wikilinks (was 14,530).
- **0** path/frontmatter mismatches across 11,435 notes.
- **0** open-nomenclature tokens in any `species` field.
- **0** database CHECK violations loading the entire vault.

## Follow-ups — now completed

All three items previously listed as scoped-but-not-done are finished.

**Species-level WoRMS crossmatch** (`scripts/worms_match.py`). All 11,435 species
crossmatched; results cached in `data/worms_species.json`. Every note now carries
`worms_status` (and `worms_aphia_id`/`worms_url` where WoRMS has a record,
10,921 of them; the 514 without are the fossils WoRMS doesn't register), plus
`worms_accepted` when WoRMS supersedes the vault's name. The vault-wide figure
the audit could only sample:

| status | n | % |
|---|---:|---:|
| accepted | 10,344 | 90.46% |
| no record (fossils) | 514 | 4.49% |
| **not accepted** | **577** | **5.05%** |

The stratified sample predicted 4.7%; the true figure is 5.05%. The 577 break
down as taxon inquirendum 138, superseded combination 131, alternative
representation 122, junior subjective synonym 53, uncertain 49, unaccepted 31,
misspellings 28, nomen nudum 19, other 6. This gives criterion **II.1** a real
taxonomic-status field and **IV.1** a second authority.

**Authorship years.** 73 of the 94 GBIF-truncated authorships were backfilled
from the fuller WoRMS authority string. The remaining 21 lack a year in WoRMS
too and were left as they are rather than guessed.

**Per-claim citations** (`data/ecology.json`, criterion **IV.2**). 22 of 24
entries now cite a published source via `source_refs` keys into a normalized
`references` block — 13 works, 12 with DOIs. Every citation's metadata was
generated from the CrossRef API response for its DOI, not transcribed, so none
is recalled from memory. Schmalfuss (1984) is the one entry without a DOI (it
predates registration) and is marked `verified: "manual"` rather than given a
fabricated identifier. The two remaining entries (`Merulanella *`, `Cubaris *`)
are hobby-genus wildcards with no located literature and carry an explicit
`source_note` saying so. Citations surface in the vault via `ecology_evidence`
(`refs:<keys>`) and a Sources section on the atlas hub.

Two claims the accuracy audit flagged as unsourced now have their actual
sources: the *Cylisticus convexus* "feminizable by wVulC" claim is Badawi, Grève
& Cordaux (2015) — the transinfection experiment itself — and the *Trichoniscus
pusillus* triploid/diploid system is Fussey (1984).

`scripts/build_db.py` loads `reference_source`, `ecology_claim` and
`ecology_claim_source`, so citation provenance is enforced by FOREIGN KEY.

## Resolving the 577 WoRMS-unaccepted names

`scripts/resolve_synonyms.py` acts on the crossmatch. "Resolving" is not one
operation — a blanket rename would have introduced errors — so the 577 are
classified and treated per class:

| action | n | what happens |
|---|---:|---|
| **RENAME** | 105 | same animal, new name (new genus combination or corrected misspelling). Note moved to the accepted binomial and into the accepted genus/family directory via `git mv`; old name kept in `former_name` and as an Obsidian `aliases` entry so existing links still resolve. |
| **MERGED** | 19 | rename target already existed → converted to a synonym record instead of duplicating a species. |
| **SYNONYM** | 78 | junior synonym of a *different* taxon → `type: synonym`, `accepted_name`, excluded from species counts. |
| **DEMOTED** | 45 | now a subspecies of another species → synonym record (the vault does not carry subspecies as notes). |
| **SUBSP_REPR** | 100 | WoRMS also carries the *nominotypical* subspecies (`Alpioniscus absoloni` → `… absoloni absoloni`). The species name is valid — **renaming these would be wrong** — so annotated only. |
| **UNPLACEABLE** | 28 | accepted placement is `Family incertae sedis <epithet>`; the genus is dissolved and there is no binomial to move to. Annotated. |
| **FLAG_ONLY** | 202 | *taxon inquirendum* / *uncertain* / *nomen nudum* with no alternative name. Nothing to move. |

Result — the accepted-species tree is now **11,293 notes** (142 synonym records
are documented in place but no longer counted), and WoRMS acceptance rose from
**90.46% → 92.48%**:

| status | n | % |
|---|---:|---:|
| accepted | 10,444 | 92.48% |
| no record (fossils) | 514 | 4.55% |
| taxon inquirendum / uncertain / nomen nudum / dubium | 206 | 1.82% |
| alternative representation (valid species) | 101 | 0.89% |
| unplaceable genus | 28 | 0.25% |

Every one of the 335 residual cases is one that **cannot** be mechanically
resolved: 206 are names of doubtful identity with no alternative, 101 are valid
species whose only "issue" is that WoRMS also lists their nominotypical
subspecies, and 28 have no accepted binomial to move to. All are annotated with
`worms_status` and a `worms_note` explaining why.

Counting is consistent end to end: `isopoda_index.py`, `atlas.py`,
`worms_match.py` and `build_db.py` all exclude `type: synonym` notes from
accepted-species counts (via `_vault.species_note_paths()`), while `build_db.py`
still loads them as rows with `status='synonym'` and their accepted name, so the
database records every name and its verdict.

## Closing the GBIF coverage gap

`scripts/place_missing.py` files the 59 GBIF-accepted species the family-first
crawl could not reach (49 carry no family in the GBIF backbone; 10 were simply
absent). Placements are recorded in `data/unplaced_species.json` and were
resolved in this order: a real WoRMS family (5); WoRMS's superfamily-level
placement kept as an explicit placeholder family with its suborder verified via
`AphiaClassification` (38 — `Janiroidea incertae sedis` → Asellota,
`Cryptoniscoidea incertae sedis` → Epicaridea, `Oniscidea incertae sedis` →
Oniscidea, `Phreatoicidea incertae sedis` → Phreatoicidea); GBIF's family (4);
otherwise `Isopoda incertae sedis` with `realm: unknown` — undetermined rather
than guessed (12). Of that last group, **7 are confirmed fossils against
PaleoBioDB** with age ranges (Triassic–Miocene); the other 5 carry no `extinct`
flag because no source confirms one.

Placeholder families are registered in the family map with `placeholder: true`
so they never read as real taxa. Coverage against GBIF is now **11,494 / 11,494**
— zero missing.

## Remaining known limitations

- 21 authorships still lack a publication year (absent from both GBIF and WoRMS).
- 12 species have no family-level placement in any consulted authority and sit
  under `Isopoda incertae sedis`; 5 of those have no record in WoRMS or
  PaleoBioDB at all, so their `realm` is `unknown` rather than assumed.
- `Merulanella *` and `Cubaris *` remain genus-wildcard ecology rows; as the
  audit noted, hobby "Cubaris" is not a monophyletic grouping.
- The 514 fossil taxa have no WoRMS record by design (WoRMS registers extant
  taxa); they are flagged `extinct` and excluded from the ecology axes.
