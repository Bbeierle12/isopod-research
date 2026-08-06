# Isopod Repository Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the stale local vault with current GitHub `main`, close the remaining reproducibility and taxonomy-integrity defects, restore enforceable CI, correct public metadata, and make provenance claims match the implemented database.

**Architecture:** Work from a clean worktree based on remote commit `867b2ce` or newer; never repair the stale checkout in place. Add a standard-library `unittest` corpus suite that treats the generated vault as a database with invariants, then fix each violated invariant at its source generator or migration. Generated files are rebuilt only after source inputs and generators pass focused tests.

**Tech Stack:** Python 3.11+, standard-library `unittest`, JSON, SQLite, Obsidian Markdown/YAML frontmatter, Git, GitHub Actions, GBIF/WoRMS-derived data.

## Global Constraints

- Preserve all user-authored note bodies and every nonblank user-owned frontmatter value.
- Never force-push or reset the stale local checkout; preserve its uncommitted files before reconciliation.
- `data/isopods.json` remains the canonical hobby catalog; `data/isopods.csv`, `Hobby/`, and `Maps/` remain generated views.
- Scientific identity invariants: path genus = `genus` frontmatter = first word of `scientificName`; open nomenclature never appears in `species`.
- Research values remain blank until researched; do not infer species-level ecology from family membership.
- All generators must be content-idempotent and support a non-mutating verification mode where practical.
- Use atomic LF-preserving writes through `scripts/_vault.py`.
- Do not add third-party Python dependencies; CI must run with the standard library.
- Commit after every task; do not mix generated-data migrations with unrelated documentation changes.

---

## File Structure

- `tests/test_catalog.py`: canonical hobby JSON/CSV identity and open-nomenclature invariants.
- `tests/test_taxonomy_tree.py`: path/frontmatter, GBIF identity, family-map, and index-count invariants.
- `tests/test_generators.py`: seed safety and clean-tree/idempotency checks.
- `tests/test_docs.py`: README, entry-point, and generated-index count consistency.
- `.github/workflows/verify.yml`: compilation, tests, database load, and generator dry-run checks.
- `scripts/seed.py`: bootstrap-only catalog creation with safe overwrite behavior and current schema.
- `scripts/repair_genus_placements.py`: deterministic migration for misplaced scientific notes.
- `scripts/build_db.py`: SQLite schema aligned with `data/schema.sql`, including normalized references.
- `data/ecology.json`: research claims linked to normalized source IDs.
- `data/references.json`: normalized citation records used by ecology claims and the database loader.
- `README.md`, `Isopods.md`: generated-count and pipeline documentation.
- `.gitignore`: ignores local SQLite outputs and Python caches.

---

### Task 1: Preserve Local Work and Establish a Clean Execution Worktree

**Files:**
- Read: `C:/Users/Bbeie/Downloads/Insect and Reptile research/`
- Create outside repository: `C:/Users/Bbeie/Downloads/isopod-local-recovery/`
- Worktree: `C:/Users/Bbeie/Downloads/isopod-remediation-worktree/`

**Interfaces:**
- Consumes: stale local checkout at `9105a0c`; remote `main` at `867b2ce` or newer.
- Produces: a recovery bundle plus a clean `remediation` branch based on current `origin/main`.

- [ ] **Step 1: Record the stale checkout state without changing it**

```powershell
$repo = 'C:\Users\Bbeie\Downloads\Insect and Reptile research'
$recovery = 'C:\Users\Bbeie\Downloads\isopod-local-recovery'
New-Item -ItemType Directory -Path $recovery -ErrorAction Stop
git -C $repo status --short | Set-Content "$recovery\status.txt"
git -C $repo rev-parse HEAD | Set-Content "$recovery\local-head.txt"
git -C $repo diff --binary | Set-Content "$recovery\tracked-changes.patch"
git -C $repo ls-files --others --exclude-standard | Set-Content "$recovery\untracked-files.txt"
```

Expected: `status.txt` records the duplicate Hobby notes and Obsidian artifacts; no repository file changes.

- [ ] **Step 2: Copy untracked files into the recovery bundle**

```powershell
$repo = 'C:\Users\Bbeie\Downloads\Insect and Reptile research'
$recovery = 'C:\Users\Bbeie\Downloads\isopod-local-recovery\untracked'
New-Item -ItemType Directory -Path $recovery -ErrorAction Stop
git -C $repo ls-files --others --exclude-standard | ForEach-Object {
  $src = Join-Path $repo $_
  $dst = Join-Path $recovery $_
  New-Item -ItemType Directory -Path (Split-Path $dst) -Force | Out-Null
  Copy-Item -LiteralPath $src -Destination $dst
}
```

Expected: every path listed in `untracked-files.txt` exists under `isopod-local-recovery/untracked/`.

- [ ] **Step 3: Fetch remote and create a clean worktree**

```powershell
$repo = 'C:\Users\Bbeie\Downloads\Insect and Reptile research'
$worktree = 'C:\Users\Bbeie\Downloads\isopod-remediation-worktree'
git -C $repo fetch origin main
git -C $repo worktree add -b remediation $worktree origin/main
git -C $worktree status --short
```

Expected: clean output from `git status --short`; `git rev-parse HEAD` equals `git rev-parse origin/main`.

- [ ] **Step 4: Copy this plan into the clean worktree if it is not already on remote**

```powershell
$src = 'C:\Users\Bbeie\Downloads\Insect and Reptile research\docs\superpowers\plans\2026-08-05-isopod-repository-remediation.md'
$dst = 'C:\Users\Bbeie\Downloads\isopod-remediation-worktree\docs\superpowers\plans\2026-08-05-isopod-repository-remediation.md'
if (-not (Test-Path $dst)) { Copy-Item -LiteralPath $src -Destination $dst }
```

- [ ] **Step 5: Commit only the plan on the clean branch**

```powershell
git -C $worktree add docs/superpowers/plans/2026-08-05-isopod-repository-remediation.md
git -C $worktree commit -m "docs: add repository remediation plan"
```

---

### Task 2: Add Corpus Invariants and Restore CI

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/helpers.py`
- Create: `tests/test_catalog.py`
- Create: `tests/test_taxonomy_tree.py`
- Create: `tests/test_docs.py`
- Create: `.github/workflows/verify.yml`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `python -m unittest discover -s tests -v` as the canonical local/CI verification command.
- Produces: helpers `read_frontmatter(path) -> dict[str, str]` and `species_notes(root) -> list[Path]`.

- [ ] **Step 1: Add shared test helpers**

```python
# tests/helpers.py
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def read_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise AssertionError(f"missing frontmatter: {path}")
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            key, value = line.split(":", 1)
            result[key] = value.strip().strip('"')
    return result

def species_notes(root: Path | None = None) -> list[Path]:
    base = root or ROOT / "Isopoda"
    return sorted(p for p in base.rglob("*.md") if not p.name.startswith("_"))
```

- [ ] **Step 2: Write failing catalog tests**

```python
# tests/test_catalog.py
import csv, json, unittest
from tests.helpers import ROOT

class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "data/isopods.json").read_text(encoding="utf-8"))["records"]

    def test_open_nomenclature_is_not_species(self):
        forbidden = {"sp.", "spp.", "cf.", "aff.", "var.", "nr."}
        bad = [r["id"] for r in self.records if r.get("species") in forbidden]
        self.assertEqual([], bad)

    def test_provisional_forms_have_open_nomenclature(self):
        bad = [r["id"] for r in self.records
               if not r.get("is_described") and r.get("open_nomenclature") != "sp."]
        self.assertEqual([], bad)

    def test_csv_identity_matches_json(self):
        with (ROOT / "data/isopods.csv").open(encoding="utf-8", newline="") as handle:
            csv_ids = {row["id"] for row in csv.DictReader(handle)}
        self.assertEqual({r["id"] for r in self.records}, csv_ids)
```

- [ ] **Step 3: Write failing taxonomy-tree tests**

```python
# tests/test_taxonomy_tree.py
import collections, json, re, unittest
from tests.helpers import ROOT, read_frontmatter, species_notes

class TaxonomyTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notes = species_notes()
        cls.family_map = json.loads((ROOT / "data/isopoda_suborders.json").read_text(encoding="utf-8"))["families"]

    def test_path_and_frontmatter_identity_agree(self):
        bad = []
        for path in self.notes:
            fm = read_frontmatter(path)
            scientific = fm["scientificName"]
            expected_genus = scientific.split()[0]
            if path.stem != scientific or path.parent.name != expected_genus or fm.get("genus") != expected_genus:
                bad.append(str(path.relative_to(ROOT)))
        self.assertEqual([], bad)

    def test_gbif_ids_are_present_and_unique(self):
        seen = collections.defaultdict(list)
        for path in self.notes:
            gbif_id = read_frontmatter(path).get("gbif_id")
            self.assertTrue(gbif_id, str(path))
            seen[gbif_id].append(str(path.relative_to(ROOT)))
        self.assertEqual({}, {key: value for key, value in seen.items() if len(value) > 1})

    def test_families_are_mapped(self):
        bad = []
        for path in self.notes:
            family = read_frontmatter(path).get("family")
            if family not in self.family_map:
                bad.append((str(path.relative_to(ROOT)), family))
        self.assertEqual([], bad)
```

- [ ] **Step 4: Write count-consistency tests**

```python
# tests/test_docs.py
import re, unittest
from tests.helpers import ROOT, read_frontmatter, species_notes

class DocumentationTests(unittest.TestCase):
    def test_master_index_count_matches_tree(self):
        fm = read_frontmatter(ROOT / "Isopoda/_Isopoda Index.md")
        self.assertEqual(len(species_notes()), int(fm["species_count"]))

    def test_public_entry_points_use_generated_counts(self):
        fm = read_frontmatter(ROOT / "Isopoda/_Isopoda Index.md")
        expected = (fm["suborder_count"], fm["family_count"], fm["species_count"])
        for filename in ("README.md", "Isopods.md"):
            text = (ROOT / filename).read_text(encoding="utf-8")
            for value in expected:
                self.assertIn(value, text, f"{filename} missing current count {value}")
```

- [ ] **Step 5: Run tests and verify the known failures**

```powershell
python -m unittest discover -s tests -v
```

Expected: catalog tests pass against current remote data; taxonomy identity test reports the 25 misplaced notes; documentation test reports stale counts.

- [ ] **Step 6: Restore the GitHub Actions workflow**

```yaml
# .github/workflows/verify.yml
name: verify

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Compile scripts
        run: python -m compileall -q scripts
      - name: Run corpus tests
        run: python -m unittest discover -s tests -v
      - name: Verify database constraints
        run: python scripts/build_db.py
      - name: Verify Atlas dry run
        run: python scripts/atlas.py --dry-run
      - name: Require clean generated tree
        run: git diff --exit-code
```

- [ ] **Step 7: Ignore local database artifacts and commit**

```text
# append to .gitignore
*.sqlite
*.sqlite3
```

```powershell
git add tests .github/workflows/verify.yml .gitignore
git commit -m "test: enforce repository corpus invariants"
```

---

### Task 3: Make `seed.py` Safe and Schema-Current

**Files:**
- Modify: `scripts/seed.py:1-160`
- Create: `tests/test_seed.py`
- Modify: `README.md:41-53`

**Interfaces:**
- Produces: `seed.build_records() -> list[dict]`.
- Produces CLI: `python scripts/seed.py --output PATH [--force]`.
- Existing `data/isopods.json` must not be overwritten without `--force`.

- [ ] **Step 1: Write failing seed tests**

```python
# tests/test_seed.py
import tempfile, unittest
from pathlib import Path
from scripts import seed

class SeedTests(unittest.TestCase):
    def test_provisional_records_use_open_nomenclature(self):
        provisional = [r for r in seed.build_records() if not r["is_described"]]
        self.assertTrue(provisional)
        self.assertTrue(all(r["species"] == "" for r in provisional))
        self.assertTrue(all(r["open_nomenclature"] == "sp." for r in provisional))

    def test_existing_output_requires_force(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "isopods.json"
            output.write_text("preserve me", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                seed.write_catalog(output, seed.build_records(), force=False)
            self.assertEqual("preserve me", output.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run the seed tests and verify they fail**

```powershell
python -m unittest tests.test_seed -v
```

Expected: failure because `build_records` and `write_catalog` do not exist.

- [ ] **Step 3: Refactor seed generation into functions**

```python
# scripts/seed.py — replace module-level writing with these interfaces
def build_records():
    records = []
    # Move the existing loops into this function.
    # For provisional forms emit:
    # "species": "", "open_nomenclature": "sp."
    return records

def write_catalog(output, records, force=False):
    output = Path(output)
    if output.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing catalog: {output}")
    payload = json.dumps({"schema_version": 1, "records": records}, indent=1, ensure_ascii=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8", newline="\n")
```

Add `argparse` with `--output` defaulting to `data/isopods.json` and `--force` as `store_true`. Put all execution under `if __name__ == "__main__":` so importing the module never writes files.

- [ ] **Step 4: Run focused and full tests**

```powershell
python -m unittest tests.test_seed tests.test_catalog -v
python -m unittest discover -s tests -v
```

Expected: seed/catalog tests pass; only the known genus-placement and documentation failures remain.

- [ ] **Step 5: Correct pipeline documentation**

Replace the README pipeline entry with:

```text
# Bootstrap only; do NOT include in routine regeneration:
python scripts/seed.py --output data/isopods.bootstrap.json

# Routine pipeline:
python scripts/validate.py
python scripts/husbandry.py
python scripts/generate.py
python scripts/atlas.py
python scripts/build_db.py
```

- [ ] **Step 6: Commit**

```powershell
git add scripts/seed.py tests/test_seed.py README.md
git commit -m "fix: make catalog bootstrap safe and schema-current"
```

---

### Task 4: Repair the 25 Genus-Placement Mismatches

**Files:**
- Create: `scripts/repair_genus_placements.py`
- Modify generated paths under: `Isopoda/Oniscidea/`
- Regenerate: `Isopoda/**/_*.md`

**Interfaces:**
- Produces: `find_mismatches() -> list[tuple[Path, Path, str]]`, where entries are old path, correct path, and expected genus.
- CLI defaults to dry-run; `--apply` performs atomic moves/frontmatter updates.

- [ ] **Step 1: Add a focused failing test for the migration detector**

```python
# append to tests/test_taxonomy_tree.py
def test_known_setaphora_is_not_nested_under_anchiphiloscia(self):
    wrong = ROOT / "Isopoda/Oniscidea/Philosciidae/Anchiphiloscia/Setaphora buddelundi.md"
    self.assertFalse(wrong.exists())
```

- [ ] **Step 2: Run the focused test**

```powershell
python -m unittest tests.test_taxonomy_tree.TaxonomyTreeTests.test_known_setaphora_is_not_nested_under_anchiphiloscia -v
```

Expected: FAIL because the wrong path exists.

- [ ] **Step 3: Implement the detector and migration**

```python
# scripts/repair_genus_placements.py
import argparse
from pathlib import Path
import _vault as V

def find_mismatches():
    result = []
    for path in V.ISOPODA.rglob("*.md"):
        if path.name.startswith("_"):
            continue
        parsed = V.parse_frontmatter(V.read_text(path))
        if not parsed:
            continue
        prefix, fm, suffix = parsed
        fields = V.frontmatter_dict(fm)
        scientific = fields.get("scientificName", path.stem)
        expected_genus = scientific.split()[0]
        if path.parent.name != expected_genus or fields.get("genus") != expected_genus:
            target = path.parent.parent / V.safe(expected_genus) / f"{V.safe(scientific)}.md"
            result.append((path, target, expected_genus))
    return result
```

For `--apply`, update only the `genus:` frontmatter line through `_vault`, create the target genus directory, refuse if the target exists with different content, then use `path.replace(target)`. Do not delete source genus directories until indexes are rebuilt.

- [ ] **Step 4: Dry-run and inspect the exact migration set**

```powershell
python scripts/repair_genus_placements.py
```

Expected: exactly 25 moves, including `Setaphora`, `Buddelundiscus`, `Euphiloscia`, `Sphaerilloides`, and `Anomaloniscus` records.

- [ ] **Step 5: Apply migration and rebuild indexes**

```powershell
python scripts/repair_genus_placements.py --apply
python scripts/isopoda_index.py
python scripts/atlas.py
```

- [ ] **Step 6: Verify corpus and Wikilinks**

```powershell
python -m unittest tests.test_taxonomy_tree -v
python -m unittest discover -s tests -v
git diff --check
```

Expected: zero path/frontmatter mismatches; no duplicate scientific names or GBIF IDs.

- [ ] **Step 7: Commit migration and generator together**

```powershell
git add scripts/repair_genus_placements.py tests/test_taxonomy_tree.py Isopoda Maps
git commit -m "fix: align Oniscidea genus paths with scientific names"
```

---

### Task 5: Make Counts Single-Sourced and Correct Public Metadata

**Files:**
- Modify: `README.md`
- Modify: `Isopods.md`
- Modify: `scripts/isopoda_index.py`
- Modify: `tests/test_docs.py`
- Remote metadata: GitHub repository description

**Interfaces:**
- Consumes: frontmatter from `Isopoda/_Isopoda Index.md`.
- Produces: public-facing counts that agree with generated index values: currently 12 suborders, 145 families, 1,597 genera, 11,435 species.

- [ ] **Step 1: Confirm documentation tests fail before editing**

```powershell
python -m unittest tests.test_docs -v
```

Expected: failures for stale 11/154/~11,500 values.

- [ ] **Step 2: Update entry-point counts**

Use the exact values in `Isopoda/_Isopoda Index.md`; do not retain approximate totals. Update both the scientific-taxonomy section and Atlas scope in `README.md`, and the master-index link text in `Isopods.md`.

- [ ] **Step 3: Add generated-count markers for future updates**

Wrap the count lines with stable comments:

```markdown
<!-- BEGIN GENERATED ISOPODA COUNTS -->
**12 suborders · 145 families · 1,597 genera · 11,435 accepted species**
<!-- END GENERATED ISOPODA COUNTS -->
```

Extend `scripts/isopoda_index.py` to replace this marked block in both files whenever it rebuilds the order index.

- [ ] **Step 4: Run documentation and full tests**

```powershell
python scripts/isopoda_index.py
python -m unittest tests.test_docs -v
python -m unittest discover -s tests -v
```

- [ ] **Step 5: Update the GitHub repository description**

```powershell
gh repo edit Bbeierle12/isopod-research --description "Open Obsidian dataset for Isopoda: 12 suborders, 145 families, 11,435 GBIF-derived species, hobby husbandry, and evidence-graded ecology maps"
```

- [ ] **Step 6: Commit**

```powershell
git add README.md Isopods.md scripts/isopoda_index.py tests/test_docs.py
git commit -m "docs: synchronize public taxonomy counts"
```

---

### Task 6: Align SQLite With the Published Provenance Schema

**Files:**
- Create: `data/references.json`
- Modify: `data/ecology.json`
- Modify: `scripts/build_db.py`
- Modify: `tests/test_catalog.py`
- Modify: `README.md`

**Interfaces:**
- `data/references.json`: `{ "references": [{"id": str, "citation": str, "doi": str, "url": str, "kind": str}] }`.
- Each ecology entry produces `sources: {"stratum": [id], "trophic": [id], "life": [id]}`.
- SQLite adds `reference_source` and `ecology_claim` with foreign keys.

- [ ] **Step 1: Add provenance tests**

```python
# append to tests/test_catalog.py
def test_every_non_c_ecology_claim_has_a_source(self):
    ecology = json.loads((ROOT / "data/ecology.json").read_text(encoding="utf-8"))["entries"]
    for entry in ecology:
        sources = entry.get("sources", {})
        for axis, grade_key in (("stratum", "stratum"), ("trophic", "trophic"), ("life", "life")):
            grade = entry.get("evd", {}).get(grade_key, "")
            if grade and "c" not in grade:
                self.assertTrue(sources.get(axis), f"{entry['match']}:{axis}")

def test_ecology_source_ids_exist(self):
    refs = json.loads((ROOT / "data/references.json").read_text(encoding="utf-8"))["references"]
    known = {r["id"] for r in refs}
    ecology = json.loads((ROOT / "data/ecology.json").read_text(encoding="utf-8"))["entries"]
    used = {source for entry in ecology for ids in entry.get("sources", {}).values() for source in ids}
    self.assertEqual(set(), used - known)
```

- [ ] **Step 2: Run tests to expose missing claim citations**

```powershell
python -m unittest tests.test_catalog.CatalogTests.test_every_non_c_ecology_claim_has_a_source -v
```

Expected: FAIL for existing `a`/`b` claims with no `sources` mapping.

- [ ] **Step 3: Normalize the existing research bibliography**

Create `data/references.json` from the bibliography already present in `Research/Isopod Categorization & Research Outline.md` and `Research/Isopod Species Ecology Data.md`. IDs must be stable slugs such as `schmalfuss-1984`, `dimitriou-taiti-sfenthourakis-2019`, and `leclercq-2016`; include DOI or URL when the source document provides it.

- [ ] **Step 4: Attach source IDs to every supported ecology claim**

For each entry in `data/ecology.json`, add the three-axis `sources` object. A grade containing only `c` may use an empty list because it explicitly means unstudied; every `a`, `a/b`, or `b` claim must cite at least one source.

- [ ] **Step 5: Extend the SQLite schema in `build_db.py`**

Add:

```sql
CREATE TABLE reference_source (
    reference_id TEXT PRIMARY KEY,
    citation TEXT NOT NULL UNIQUE,
    doi TEXT,
    url TEXT,
    kind TEXT
);
CREATE TABLE ecology_claim (
    taxon_match TEXT NOT NULL,
    axis TEXT NOT NULL CHECK(axis IN ('stratum','trophic','life')),
    value TEXT NOT NULL,
    evidence_grade TEXT NOT NULL,
    reference_id TEXT REFERENCES reference_source(reference_id),
    UNIQUE(taxon_match, axis, reference_id)
);
```

Implement `load_references(cur) -> int` and `load_ecology_claims(cur) -> int`; call them before `con.commit()`. Print loaded reference/claim counts and fail when a non-`c` claim has no reference.

- [ ] **Step 6: Run provenance and database verification**

```powershell
python -m unittest tests.test_catalog -v
python scripts/build_db.py
```

Expected: zero missing source IDs, zero dangling foreign keys, zero CHECK violations, zero identity collisions.

- [ ] **Step 7: Narrow or substantiate README claims**

Change “cited research layer” to “claim-level cited research layer” only after the tests pass. Document that `c` denotes explicitly unstudied/inferred data rather than a sourced fact.

- [ ] **Step 8: Commit**

```powershell
git add data/references.json data/ecology.json scripts/build_db.py tests/test_catalog.py README.md
git commit -m "feat: add claim-level ecology provenance"
```

---

### Task 7: Surface Upstream Authorship Quality Without Fabricating Data

**Files:**
- Modify: `scripts/taxonomy.py`
- Modify: `scripts/build_db.py`
- Modify: `tests/test_taxonomy_tree.py`
- Regenerate only affected species notes with `scripts/taxonomy.py --refresh`

**Interfaces:**
- Produces note fields `authorship_quality: complete|missing|missing_year` and `authorship_source: GBIF`.
- Does not invent missing years or authors.

- [ ] **Step 1: Add authorship classification tests**

```python
# append to tests/test_taxonomy_tree.py
def test_every_species_has_authorship_quality(self):
    allowed = {"complete", "missing", "missing_year"}
    bad = []
    for path in self.notes:
        value = read_frontmatter(path).get("authorship_quality")
        if value not in allowed:
            bad.append(str(path.relative_to(ROOT)))
    self.assertEqual([], bad)
```

- [ ] **Step 2: Add a pure classifier to `taxonomy.py`**

```python
def authorship_quality(auth):
    auth = (auth or "").strip()
    if not auth:
        return "missing"
    return "complete" if re.search(r"\b(?:17|18|19|20)\d{2}\b", auth) else "missing_year"
```

Include both fields in `render_note`; when refreshing, preserve note body and user-owned fields through `_vault` rather than replacing the entire note.

- [ ] **Step 3: Refresh taxonomy notes and verify exact debt counts**

```powershell
python scripts/taxonomy.py --refresh
python -m unittest tests.test_taxonomy_tree -v
```

Expected baseline before upstream correction: approximately 76 `missing`, 18 additional `missing_year` beyond those blanks, totaling 94 without a detected year. Record exact post-refresh counts in `docs/reviews/`.

- [ ] **Step 4: Extend SQLite ingestion**

Add `authorship_quality` to the SQLite taxonomy table and load it from frontmatter. Add a demonstration query grouping species by quality.

- [ ] **Step 5: Commit**

```powershell
git add scripts/taxonomy.py scripts/build_db.py tests/test_taxonomy_tree.py Isopoda docs/reviews
git commit -m "feat: expose upstream authorship completeness"
```

---

### Task 8: Repository Cleanup and Final Release Verification

**Files:**
- Delete: `scripts/build_suborders.py`
- Delete if unchanged defaults: `Untitled.md`, `Untitled.canvas`, `Welcome.md`
- Modify: `.gitignore`
- Modify: `README.md`
- Verify: all generated files

**Interfaces:**
- Produces: clean public repository with enforced CI and no placeholder artifacts.

- [ ] **Step 1: Confirm placeholder files contain no user data**

```powershell
Get-Item scripts/build_suborders.py,Untitled.md,Untitled.canvas,Welcome.md | Select-Object Name,Length
Get-Content Untitled.canvas,Welcome.md
```

Expected: `build_suborders.py` and `Untitled.md` are empty; canvas/welcome are unchanged Obsidian defaults.

- [ ] **Step 2: Remove confirmed placeholders**

```powershell
git rm scripts/build_suborders.py Untitled.md Untitled.canvas Welcome.md
```

- [ ] **Step 3: Run the complete routine pipeline without `seed.py`**

```powershell
python scripts/validate.py
python scripts/husbandry.py
python scripts/generate.py
python scripts/atlas.py
python scripts/isopoda_index.py
python scripts/build_db.py
```

- [ ] **Step 4: Run all tests and check the generated diff**

```powershell
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
git diff --check
git status --short
```

Expected: tests pass; status contains only the intentional cleanup and deterministic generated changes from this task.

- [ ] **Step 5: Commit cleanup**

```powershell
git add -A
git commit -m "chore: remove placeholder artifacts and finalize verification"
```

- [ ] **Step 6: Push branch and open a pull request**

```powershell
git push -u origin remediation
gh pr create --base main --head remediation --title "Repository remediation: reproducibility, taxonomy integrity, and provenance" --body "Implements the 2026-08-05 remediation plan: safe seed bootstrap, corpus invariants and CI, 25 genus-placement repairs, synchronized public counts, claim-level provenance, authorship-quality flags, and repository cleanup."
```

- [ ] **Step 7: Require green CI before merge**

```powershell
gh pr checks --watch
```

Expected: `verify` passes at the PR head. Do not merge while any check is pending or failing.

- [ ] **Step 8: Enable branch protection after the workflow exists on `main`**

Configure `main` to require pull requests, one approval, and the `verify` status check. Confirm direct pushes are blocked by querying:

```powershell
gh api repos/Bbeierle12/isopod-research/branches/main/protection
```

---

## Final Acceptance Criteria

- Local user work is preserved outside the stale checkout before any branch manipulation.
- Current GitHub `main` is the sole base for implementation.
- `python -m unittest discover -s tests -v` passes locally and in GitHub Actions.
- No species note has path/genus/scientific-name disagreement.
- No catalog record stores `sp.` or another open-nomenclature token in `species`.
- `seed.py` cannot overwrite the canonical catalog without explicit `--force`.
- README, `Isopods.md`, and `_Isopoda Index.md` report the same exact counts.
- Current remote `main` contains `.github/workflows/verify.yml`, and the merge commit receives a green run.
- SQLite implements normalized references and rejects unsupported non-`c` ecology claims.
- Missing upstream authorship is labeled, never invented.
- Full routine regeneration (excluding bootstrap `seed.py`) is content-idempotent.
- Repository has no empty scripts or default Obsidian placeholder files.
