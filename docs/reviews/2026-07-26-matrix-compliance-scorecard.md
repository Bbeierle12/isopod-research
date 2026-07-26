# Evaluation-matrix compliance scorecard — Isopoda vault

**Applies:** the four-section evaluation matrix (ICZN nomenclature, taxonomic validity, normalization,
provenance) to the vault at `b8c80cf`.
**Corpus:** 11,435 species notes under `Isopoda/`, plus `Hobby/` (61 forms), `data/isopoda_suborders.json`
and `data/ecology.json`.
**Method:** every threshold below was executed as a check over the whole corpus, not spot-checked.
Counts are exact. Authority = WoRMS + GBIF Backbone, queried live.

## Scorecard

| Criterion | Verdict | Evidence (n = 11,435 unless noted) |
|---|---|---|
| **I.1** Binomial/Trinomial formatting | ✅ **Pass** | 0 fails. Every `scientificName` matches `^[A-Z][a-z]+ [a-z…]$`. |
| **I.2** Author citation syntax | ⚠️ **Partial** | Parenthesization faithful & ICZN-correct where checkable; but 76 empty + 94 (0.82%) missing the year, 57 truncated — all inherited verbatim from GBIF. No parens flag. |
| **I.3** Orthographic consistency | ⚠️ **Partial** | Matches GBIF spelling exactly, but GBIF ≠ authority for ≥1 species (`Onychocepon resupinum`→`resupinus`) and 6 family-level misspelling duplicates. |
| **I.4** Abbreviations & annotations | ✅ **Pass** (tree) | 0 open-nomenclature modifiers in the 11,435 scientific notes. `Hobby/` uses `sp.` by design (24/61) but not in a dedicated remarks field. |
| **II.1** Current acceptance status | ❌ **Fail** | No taxonomic-status field. `status:` holds `stub`/`hobby` (completeness). Acceptance not stored → not re-verifiable; 4.7% of a sample not accepted in WoRMS. |
| **II.2** Hierarchical integrity | ⚠️ **Partial** | In-vault: perfect (0 path/frontmatter mismatches, 0 orphans). Vs consensus: **fails the matrix's own example** — a marine parasite family nested under Oniscidea. |
| **II.3** Homonym detection | ⚠️ **Partial** | 0 duplicate binomials, 0 genus under >1 family — but by inheritance from GBIF's tree, not by an enforced guard. No homonym mechanism. |
| **III.1** Atomization | ⚠️ **Partial** | Genus/species/family/suborder are atomic keys. Authorship is **not**: one string bundles author + year + parens. |
| **III.2** Whitespace / invisible chars | ✅ **Pass** (identity) | 0 issues, 0 zero-width/`Cf`/`Zs` chars in any identity field. (Blank research fields carry trailing WS — cosmetic, tracked in the pipeline review.) |
| **III.3** Deduplication | ✅ **Pass** | 0 duplicate species/author composites. |
| **IV.1** Authority cross-reference | ⚠️ **Partial** | `gbif_id` + `gbif_url` on 100%. WoRMS AphiaID / ITIS TSN on **0%**. Single-authority. |
| **IV.2** Source citation | ❌ **Fail** | No per-record reference link. One file-level `_source` string on the family map; none on `ecology.json`. |

**Tally:** 4 Pass · 6 Partial · 2 Fail. Nothing in Section I–III is a *formatting* or *integrity*
disaster — the mechanical hygiene is genuinely good. The two hard Fails (II.1, IV.2) and the sharpest
Partials (I.2, IV.1) are all the same root cause: **the vault records GBIF's answer but never records
that it is GBIF's answer, nor lets you re-check it.**

---

## Section I — Nomenclatural compliance (ICZN)

**I.1 — Pass, unqualified.** A regex for capitalized genus + lowercase epithet over all 11,435
`scientificName` values returned **0 failures**. No `Armadillidium Vulgare`, no all-caps, no
lowercase genus. The `safe()` filename sanitiser never altered a case. This is the cleanest result
in the matrix.

**I.2 — Partial fail, and the interesting one.** Two sub-claims, opposite verdicts:

- *Parenthesization is correct.* 25.8% of authored notes (2,933) are parenthesized, 74.2% (8,426)
  are not — and the split is meaningful, not noise. Ground-truth spot checks all pass, including the
  trap: `Ligia oceanica` → `(Linnaeus, 1767)` is **correct** because Linnaeus described it as
  *Oniscus oceanicus* and it was later moved to *Ligia*. `Armadillidium vulgare` → `(Latreille,
  1804)` (moved from *Armadillo*) parenthesized; `Porcellio scaber` → `Latreille, 1804` (original
  combination) not. The parenthetical-authorship rule of ICZN Art. 51.3 is being honoured.
- *Year and completeness fail for 0.82%.* 94 notes carry an authorship with **no year**, 76 more are
  **empty**. 57 of the 94 are truncated at a name particle — e.g. `Pleurocrypta keiensis` →
  `"Nierstrasz & Brender"`. That is *Nierstrasz & Brender à Brandis, 1929*, sheared at the non-ASCII
  "à" with the year lost. **This is inherited verbatim from GBIF** — GBIF's own backbone stores
  `authorship: "Nierstrasz & Brender"` for this record (I checked the API directly). The vault is a
  faithful copy of a defective source. The damage concentrates in Bopyridae (55 of 94), consistent
  with a single bad ingestion of one epicaridean monograph into GBIF.

  Verdict against the matrix threshold ("Fail: missing year of publication"): these 94 **fail**, and
  they fail because GBIF fails. The fix is not to hand-patch 94 strings but to backfill authorship
  from WoRMS/Nomenclator at crossmatch time (§IV) and stop treating GBIF as authoritative for
  citation strings.

- *No parentheses boolean.* The matrix's database-constraint column asks for a `BOOLEAN` original-vs-
  reassigned flag. It doesn't exist — the parenthesis lives only inside the free-text string, so you
  cannot query "all reassigned combinations" without re-parsing. See III.1.

**I.3 — Partial fail.** The vault's spelling is *exactly* GBIF's, so there is no internal typo. But
the matrix's threshold is "deviations from the officially registered spelling in **primary taxonomic
literature**", and against WoRMS the vault inherits GBIF's spelling errors: `Onychocepon resupinum`
(WoRMS: `resupinus`), and — at family rank — the six misspelling twins already documented in the
classification audit (`Archeoniscidae`/`Archaeoniscidae`, `Gnathidae`/`Gnathiidae`, …). "Exact string
match against a designated authority file" passes only if that authority is GBIF; against WoRMS it
does not.

**I.4 — Pass for the scientific tree.** 0 of 11,435 notes contain `sp.`/`spp.`/`cf.`/`aff.`/`var.` in
the name. `Hobby/` legitimately uses open nomenclature (24 of 61 titles, e.g. *Merulanella* sp. "Red
Diablo") because those *are* undescribed trade forms — but the matrix wants the modifier and the
trade epithet in an "identification remarks" column, and the vault keeps them concatenated in the
note title. Correct biology, non-atomic storage.

## Section II — Taxonomic hierarchy & validity

**II.1 — Fail.** There is no field that records taxonomic acceptance. The `status:` key holds
`stub` (11,359) or `hobby` (76) — a *completeness* state, not `Accepted | Synonym | Unresolved |
Deprecated`. GBIF's `ACCEPTED` filter was applied at crawl time and then discarded: the vault
asserts acceptance by absence-of-alternative, and cannot re-verify it without re-crawling. Combined
with the sampled 4.7% WoRMS-unaccepted rate, this is the criterion most in need of a schema column.
Recommended enum exactly as the matrix specifies, plus a `accepted_name_id` self-reference for
synonyms.

**II.2 — Partial, and it fails on the matrix's own worked example.** Structurally the vault is
flawless: all 11,435 notes have `suborder/family/genus/scientificName` frontmatter identical to their
directory path (0 mismatches), and there are no orphans. But the matrix's stated Fail case is *"a
terrestrial woodlouse (Oniscidea) mistakenly nested under a marine parasitic family"* — and the vault
contains the mirror image: **Stellatoniscidae, a marine cryptoniscoid parasite, nested under
Oniscidea with `realm: terrestrial`**, plus 889 epicaridean parasite notes under Cymothoida with
Epicaridea absent entirely. The `FOREIGN KEY` nesting is internally valid; the *biology* of the
nesting is not. (Full detail in the classification audit, §A1.)

**II.3 — Partial.** The composite `Genus + Species` is unique across the corpus (0 collisions) and no
genus directory appears under two families, so the `UNIQUE` constraint would pass today. But that is a
*property inherited from GBIF's backbone*, not an *enforced guard* — nothing in the pipeline would
detect a homonym if one were introduced, and there is no replacement-name mechanism. Pass on current
data; no compliance mechanism.

## Section III — Data structure & normalization

**III.1 — Partial.** The good half: `genus`, `species`(via path), `family`, `suborder` are already
separate, queryable keys, and duplicated in the directory tree — better atomization than most working
datasets. The missing half is entirely in the author citation: `authorship: "(Latreille, 1804)"`
bundles **author + year + original-combination flag** in one string. To satisfy the matrix you need
`authorship_author`, `authorship_year` (INTEGER), and `is_reassigned` (BOOLEAN) as distinct columns.
Everything needed is already inside the string and parses cleanly (parens balanced on 100% of notes,
per III.2's sibling check) — this is a splitting exercise, not new data.

**III.2 — Pass on identity.** 0 leading/trailing/double-space issues and 0 invisible characters
(`Cf`/`Zs` category, zero-width, NBSP) across every `scientificName`, `genus`, and filename. The
"Armadillidium " vs "Armadillidium" split the matrix warns about cannot occur. (Separately, 4,226
notes carry trailing whitespace on *blank research fields* — `ecomorph: ` — which is cosmetic and
already logged in the pipeline review §5.6; it touches no identity field and no query key.)

**III.3 — Pass.** 0 duplicate species/author composites. Every biological entity has exactly one
primary note. `TRIM()`+`UNIQUE` would be satisfied as-is.

## Section IV — Provenance & authority

**IV.1 — Partial.** `gbif_id` and `gbif_url` are present and well-formed on 100% of notes — one
external authority is fully wired. But WoRMS AphiaID and ITIS TSN are absent from the schema
entirely (0%), which is precisely why Sections I.2, I.3, II.1 and II.2 keep failing *against WoRMS
while passing against GBIF*: there is only one cross-reference, and it is the one with the citation
truncations and the pre-Epicaridea suborder scheme. Adding `worms_aphia_id` upgrades four criteria at
once and is ~290 API calls for the whole corpus.

**IV.2 — Fail.** The matrix wants a `References` table with a `FOREIGN KEY` per record. The vault has:
one file-level `_source` string in `isopoda_suborders.json` ("Suborders per WoRMS; families per
GBIF…"), **nothing** in `ecology.json`, and per-note citation limited to the GBIF URL — which sources
the *name*, not the *placement* or the *ecology claim*. So the 24 hand-curated ecology entries — the
highest-value, most-contestable data in the vault, the rows a doctoral committee would probe first —
carry zero citations. This is the provenance gap that matters most, because it covers exactly the
data that isn't mechanically derivable from an API.

---

## What to change, ranked by matrix leverage

1. **Add `worms_aphia_id` + `worms_status` + `worms_accepted_name` per note** (~290 requests). Single
   change that moves I.2 (backfill years), I.3 (authority spelling), II.1 (real acceptance status),
   II.2 (Epicaridea), IV.1 (second authority) toward Pass.
2. **Add a `references` table and a per-claim `source` on all 24 `ecology.json` rows** (IV.2). Nothing
   else in the vault is as exposed to "defend this to your advisor" as uncited ecology.
3. **Split `authorship` into `author` / `year` / `is_reassigned`** (III.1, I.2 flag). Pure parsing;
   the parens are already balanced and correct.
4. **Rename the completeness field and add a taxonomic-status enum** (II.1): `Accepted | Synonym |
   Unresolved | Deprecated`, defaulting from the WoRMS crossmatch in step 1.
5. **Reconcile spelling/placement to WoRMS** for the species and families where GBIF and WoRMS
   disagree (I.3, II.2) — merge the 6 family misspelling-twins, correct `resupinum`→`resupinus`, etc.

Items 1–2 are the doctoral-defensibility core; 3–5 are the schema-constraint work the matrix's
right-hand column describes. None of the four current Passes (I.1, I.4-tree, III.2, III.3) needs any
work — the mechanical nomenclature and normalization are already sound.
