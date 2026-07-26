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

## Remaining known limitations

- The 577 WoRMS-unaccepted species are **recorded, not resolved** — each note
  states its status and accepted name, but the notes have not been renamed or
  merged. That is a taxonomic-curation decision, not a mechanical one.
- 21 authorships still lack a publication year (absent from both GBIF and WoRMS).
- `Merulanella *` and `Cubaris *` remain genus-wildcard ecology rows; as the
  audit noted, hobby "Cubaris" is not a monophyletic grouping.
