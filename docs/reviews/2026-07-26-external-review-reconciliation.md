# Reconciliation of two external reviews + schema critique

**Inputs:** two external evaluation reports and one proposed `schema.sql`, all supplied 2026-07-26.
- **Report A** — audits `data/isopods.csv`; verdict *"exceptionally clean… complies with almost all
  criteria."*
- **Report B** — audits `data/isopods.json` (hobby catalog); verdict *"not currently compliant at
  the doctoral standard,"* with a HARD FAIL on open nomenclature.
- **schema.sql** — PostgreSQL DDL implementing the matrix as constraints.

The two reports reach opposite headline verdicts on the same repository. I adjudicated every contested
claim against the actual files rather than trusting either report. Counts below are exact.

## Bottom line

**Report B is the trustworthy one. Report A's headline is materially misleading** — not because its
individual sub-checks are false, but because it silently scoped itself to *described* forms, which
excludes the exact 24 records that fail the matrix, then reported a repo-level "clean" pass. An audit
that calls `data/isopods.csv` "exceptionally clean" while `species = "sp."` sits in **24 rows of that
very CSV** cannot be relied on at the standard being applied.

That said, neither report is wholly right, and Report A caught one true item Report B missed. The
adjudication:

| Contested claim | Ground truth (verified) | Report A | Report B |
|---|---|---|---|
| `species` field contains `sp.` | **True — 24 rows**, in both `.json` and `.csv` | ✗ "Pass, none found" | ✓ HARD FAIL |
| Authority carries the year | **True for the hobby catalog** — 0 of 85 authored forms miss a year | ✓ Pass | ✗ called FAIL* |
| Authority is atomized | **False** — one string bundles author+year+parens | (not flagged) | ✓ FAIL |
| Synonym mapping is sparse | **True — exactly 1** (`armadillidium-frontirostre → Armadillidium pallasii`) | (not flagged) | ✓ |
| Described forms missing `gbif_id` | **True — exactly 3** | ✓ named all 3 | ✓ named 2 of 3 |
| Sources are a generic string | **True — all 112 forms** carry the identical string | (not flagged) | ✓ FAIL |
| Duplicate binomials | **True in the provisional layer** — `Cubaris sp.` ×8, `Merulanella sp.` ×5 | ✓ "Pass" (by id) | (not flagged) |

\* Report B's grade is defensible: its prose correctly says the problem is "no boolean flag or
separate year field" — i.e. *atomization*, not a missing year. Its label "FAIL" conflates the two,
but the underlying finding is right.

## The decisive discrepancy, in detail

Both files store open nomenclature **in the primary identity field**, which the matrix's rule
disallows verbatim ("Disallow *sp.*, *spp.*, *cf.*, *aff.*, *var.* in the primary `species_epithet`
field"):

```
data/isopods.json  record cubaris-sp-rubber-ducky : {"genus":"Cubaris","species":"sp.","trade_name":"Rubber Ducky", ...}
data/isopods.csv   row                              : Cubaris , sp. , ... , Rubber Ducky
```

24 records, identical in both serializations. Report A analyzed the CSV and reported *"No sp., spp.,
cf., aff., or var. were found inside the specific epithet column."* That statement is false for the
file it names. The report's own method line explains how: *"focusing on described form entries."* The
24 failures are all `is_described: false` / `taxon_status: provisional`, so the chosen scope removed
them — and the report then generalized a subset pass to a whole-file "exceptionally clean." At a
doctoral bar, scoping out the non-compliant records and not foregrounding that is the kind of move the
audit exists to catch, not to make.

**This also corrects my own earlier scorecard.** I graded I.4 "Pass (tree)" and noted the hobby forms
use `sp.` "by design." Both halves are factually true — the 11,435 scientific notes are clean, the
hobby catalog is not — but under the matrix applied to the whole repo, the catalog's 24 records are a
genuine I.4 **Fail**, and "by design" doesn't excuse it against a rule that names the exact tokens.
Report B is right to fail it; I should have graded the catalog, not just the tree.

## Where each report is wrong or incomplete

**Report A** — beyond the scoping problem: it credits *"no duplicate taxonomic identities (Genus +
Species + Authority)"* as a Pass, but the provisional layer has heavy binomial collisions —
`Cubaris sp.` ×8, `Merulanella sp.` ×5, plus `Troglodillo/Venezillo/Tuberillo sp.` ×2 each. They are
distinguishable *only* by `trade_name`. Report A's Pass holds only because it keyed on the record `id`
(or on described forms), not on the binomial. Its distinctive correct contribution: it named
`porcellio-sevilla` as a third gbif-less described form (`taxon_status: needs_review`), which Report B
omitted.

**Report B** — largely accurate; two small imperfections. It named 2 of the 3 gbif-less described
forms (missed `porcellio-sevilla`), and its "Author Citation Syntax = FAIL" label reads as "years
missing" when the catalog's real defect is non-atomization (years are present). Everything else it
asserts — open nomenclature, single synonym, generic sources, unmatched `paxodillidium-schmalfussi`,
authority-not-atomic — is confirmed true.

**The three gbif-less described forms**, for the record:

```
paxodillidium-schmalfussi   species=schmalfussi   status=unmatched     authority=''
porcellio-sevilla           species=sevilla       status=needs_review  authority=''
trachelipus-squamatus       species=squamatus     status=unmatched     authority=''
```

`Paxodillidium schmalfussi` and `Trachelipus squamatus` are real described species that GBIF's
backbone simply doesn't carry — the same GBIF-vs-authority gap documented for the scientific tree.
They should resolve against WoRMS, not be left `unmatched` with empty authority.

## schema.sql — assessment

It is a competent skeleton and gets the core atomization right: `authority` / `authority_year` /
`is_reassigned` as separate columns (fixes I.2 + III.1), a real `taxon_status_enum` (II.1),
`worms_id` + `itis_tsn` alongside `gbif_id` (IV.1), and CHECKs for capitalization, lowercase epithet,
open-nomenclature rejection, and whitespace. If the goal is "make the matrix rules hard constraints,"
this is the right shape. But adopting it as-is would break on this repo's own data, and it
under-implements two of the criteria it claims to encode. Four concrete problems:

1. **It cannot store the hobby catalog it is meant to validate.** `chk_species_lowercase`
   (`^[a-z]+(-[a-z]+)?$`) and `chk_no_open_nomenclature` both reject `species_epithet = 'sp.'` — but
   the schema provides **no column to relocate open nomenclature into**. The matrix's own remediation
   is "move `sp.` to a dedicated `identification_remarks` / `open_nomenclature` column"; this schema
   enforces the prohibition without creating the destination, so loading the current catalog means
   dropping all 24 provisional forms (and there is no `trade_name` column to hold what distinguishes
   them). Add `open_nomenclature VARCHAR`, `trade_name VARCHAR`, and relax the epithet CHECK to allow
   a NULL epithet when `open_nomenclature` is set.

2. **`source_citation TEXT` is the very anti-pattern IV.2 fails the repo for.** The matrix's IV.2
   constraint is a normalized `References` table reached by `FOREIGN KEY`; a free-text citation column
   is what produces the "generic source string" failure in the first place. The schema should carry a
   `references(reference_id, …)` table and a `source_ref_id` FK (or a join table for multiple
   citations per claim), not a text blob.

3. **`parent_taxon_id` is overloaded.** It is commented as hierarchical parent (genus/family), but
   `chk_synonym_must_have_parent` reuses it as the senior-synonym pointer. The matrix's II.1
   constraint is "a direct, mapped relational link to the currently accepted **senior synonym**" —
   a distinct edge from the taxonomic parent. One nullable FK cannot mean both. Add a separate
   `accepted_taxon_id INTEGER REFERENCES taxonomy(taxon_id)` and gate the synonym CHECK on that.

4. **The uniqueness guard leaks on NULL authority.** `UNIQUE (genus, species_epithet, authority)`:
   in PostgreSQL, NULLs are distinct, so every record with unknown authority — all provisional forms —
   escapes the constraint, and the `Cubaris sp.` ×8 collisions insert freely. Conversely, on populated
   authorities the constraint *blocks* legitimate secondary homonyms. Use `UNIQUE NULLS NOT DISTINCT`
   (PG 15+) or a unique index over `COALESCE(authority,'')`, and reconsider whether homonym handling
   belongs in a uniqueness constraint at all (a genuine homonym is the *same* name under a *different*
   authority — the thing this constraint is designed to forbid).

Minor: the atomization trigger rejects any `authority ~ '\d{4}'`, which is correct given the separate
year column, but nothing enforces that a parenthesized original combination sets `is_reassigned` — that
belongs in the ingest/ETL step, and the ETL is where the `sp.`→`open_nomenclature` move must happen too.

## Recommendation

Take **Report B's findings** as the accurate baseline, add Report A's one true catch
(`porcellio-sevilla`), and treat Report A's headline as a caution about scoped audits rather than a
result. Adopt the schema, but first add the `open_nomenclature` + `trade_name` columns, swap
`source_citation` for a `references` table, split out `accepted_taxon_id`, and fix the NULL-authority
uniqueness — otherwise the DDL rejects the repo's own provisional layer on first load. All four fixes
are small and mechanical; the schema's bones are sound.
