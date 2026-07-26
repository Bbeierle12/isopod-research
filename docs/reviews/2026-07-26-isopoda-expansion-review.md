# Code review — Isopoda vault expansion pipeline

**Scope:** `scripts/taxonomy.py`, `scripts/atlas.py` (pass 2), `scripts/isopoda_index.py`
**Reviewed:** 2026-07-26 · vault at `b8c80cf` · 12,057 notes / 11,435 species notes
**Method:** every finding below was reproduced against the vault on disk or against the live GBIF
API. Measurements are quoted where they matter. Findings that are real but not currently
triggered by vault data are marked **latent**.

---

## Verdict

The taxonomic output is *accurate*. A full diff of the vault against the GBIF backbone found
**0 stale notes** — nothing in `Isopoda/` that GBIF no longer accepts — and 11,435 of 11,494
accepted species present. The `ACCEPTED` filter and the suborder/realm map are doing their job.

The problems are all in the plumbing, and two of them are blockers:

| # | Severity | Finding |
|---|---|---|
| 1 | **Blocker** | `taxonomy.py` does not compile on Python ≤ 3.11 |
| 2 | **Blocker** | 14,530 broken wikilinks — family & genus index notes are linked but never generated |
| 3 | **High** | `atlas.py` `re.sub` replacement is unescaped → crash / silent content substitution |
| 4 | **High** | `atlas.py` `^key:.*$` silently destroys multi-line YAML values |
| 5 | **High** | `quote()` emits invalid YAML and wrong types; a correct version already exists in the repo |
| 6 | Medium | Crawler makes 1,138 sequential requests for work GBIF serves in 12 |
| 7 | Medium | Failed fetch is indistinguishable from end-of-data → silent, *permanent* truncation |
| 8 | Medium | Family-first crawl structurally cannot reach 49 accepted species |
| 9 | Medium | `isopoda_index.py` rewrites 12 notes on every run (date stamp) |
| 10 | Medium | Generated counts are wrong, including a visible "11448 of 11435" |
| 11 | Medium | `realm` regex reads across the newline (latent) |
| 12+ | Low | I/O shape, duplication, portability, polish — §5 |

On your four focus areas, in short: **I/O is not your bottleneck** (§1 — the full 11,435-file walk
takes 0.58 s, and the honest saving is 0.23 s); **idempotency is mostly sound but has two real
corruption paths** (§2); **API handling is the weakest part and has a 95× improvement available**
(§3); and the biggest structural win is deleting `atlas.py`'s frontmatter writers in favour of
`generate.py`'s, which already solve the same problem correctly (§4).

---

## Blockers

### 1. `taxonomy.py` does not compile on Python ≤ 3.11

```
$ python3 --version && python3 -m py_compile scripts/taxonomy.py
Python 3.11.15
  File "scripts/taxonomy.py", line 113
SyntaxError: f-string expression part cannot include a backslash
```

`taxonomy.py:79` puts a backslash inside an f-string expression:

```python
authorship: "{auth.replace('"', '\\"')}"
```

Backslashes in f-string expressions (and reusing `"` inside a `"`-delimited f-string) only became
legal in **3.12** (PEP 701). The script runs on your machine and nowhere else — no CI, no
collaborator on 3.11, no `python:3.11` container. For a repo whose README promises a repeatable
pipeline, that's the most expensive bug in the set even though it never corrupted a byte.

Hoist the escaping out of the literal:

```python
auth_yaml = json.dumps(auth or "")     # JSON strings are valid YAML flow scalars — handles " and \
...
authorship: {auth_yaml}
```

`json.dumps` is the right tool here: it escapes `"` *and* `\`, which the current code does not —
an authorship string containing a backslash produces invalid YAML today.

Worth adding a floor while you're there, so this fails loudly instead of cryptically:

```python
import sys
if sys.version_info < (3, 9):
    sys.exit("taxonomy.py requires Python 3.9+")
```

### 2. 14,530 broken wikilinks: the index notes are never generated

Every species note `taxonomy.py` writes ends its breadcrumb with two links:

```python
**Family** [[_{fam_name} Index|{fam_name}]] › **Genus** [[_{gen_name}|{gen_name}]]
```

`isopoda_index.py` writes **only** the 11 suborder indexes plus `_Isopoda Index.md`. It never
writes a family index or a genus index — but its own suborder tables link to all 154 family
indexes. Measured across `Isopoda/`:

```
distinct broken link targets : 1142
broken link instances        : 14530
  from species notes         : 14418   (7,209 family + 7,209 genus)
  from index notes           :   112
missing family-index notes   :  112 of 154
missing genus-index notes    : 1030 of 1597
```

The 42 family and 567 genus index notes that *do* exist are all under `Oniscidea/`, left over from
`generate.py`. So **every one of the 7,209 non-Oniscidea species notes has both of its
breadcrumb links broken** — the navigational spine of the expansion is 100% dead, and Obsidian's
graph view for the new tree is empty.

This also contradicts the expansion summary ("Generating hierarchical index notes for the 11
suborders and 154 families"): the family half was never implemented.

`isopoda_index.py` already walks the tree and accumulates exactly the data a family index needs
(`suborder_info[sub]["families"][fam]["genera"]` / `["species"]`), so this is an emit step, not
new logic. Two loops, ~30 lines. Do the genus indexes in the same pass — you have `gen_path` and
its species list in scope at `isopoda_index.py:37`.

---

## §2 — Idempotency (focus area 2)

Verified by running the writers twice over synthetic notes and diffing. **The good news: for the
notes currently in the vault, both writers are stable — run 1 == run 2, byte for byte.** The
`if new != t` guard before writing is the right instinct and it works.

The bad news is that stability depends on the frontmatter being simple, and two failure modes are
one hand-edit away.

### 3. High — `re.sub` replacement string is not escaped

`atlas.py:140` and `atlas.py:159`:

```python
fm = re.sub(r"^%s:.*$" % re.escape(k), "%s: %s" % (k, quote(v)), fm, count=1, flags=re.M)
```

The *pattern* is escaped; the *replacement* is not. `re.sub` interprets backslash escapes and
group references in the replacement string:

```
value r"EN\EP"        -> re.error: bad escape \E at position 19          (crashes the run)
value r"grade \1 zone"-> re.error: invalid group reference 1 at position 24
```

A value containing `\g<0>` would not crash — it would silently splice the matched line into the
value. Nothing in `data/ecology.json` contains a backslash today, so this is **latent**, but it is
a crash-on-data bug in a loop over 11,435 files: it takes one ecology entry with a Windows path,
a LaTeX fragment, or a regex in a note to abort the run partway through, leaving the tree half
written (see §5.4 — the writes aren't atomic either).

Fix is one character plus a lambda — a function replacement is never scanned for escapes:

```python
fm = re.sub(pat, lambda _m: "%s: %s" % (k, quote(v)), fm, count=1, flags=re.M)
```

### 4. High — `^key:.*$` silently destroys multi-line YAML values

`.*` with `re.M` matches to end-of-*line*, so a block value keeps its continuation lines while its
header is replaced:

```yaml
# before                          # after scaffold_fields(path, {"habitat_stratum": "CO"})
habitat_stratum:                  habitat_stratum: CO
  - EN                              - EN
  - EP                              - EP
```

The insidious part: that **still parses**. YAML folds the more-indented lines into a plain
multi-line scalar, so `yaml.safe_load` returns

```
habitat_stratum = 'CO - EN - EP'
```

No error, no warning — the list is gone and the value is nonsense. There is no YAML parse failure
for `validate.py` or Obsidian to catch.

`scaffold_fields` makes it worse. Its blank-detection reads only the header line:

```python
mm = re.search(r"^(%s:)[ \t]*(.*)$" % re.escape(k), fm, re.M)
if mm and v and not mm.group(2).strip():   # "present but blank" — but a block header is ALSO blank
```

A block-list value looks blank, so the "fill only if empty, hand edits always win" contract
inverts: a field the user carefully filled in as a list is the *one* case that gets overwritten.

No frontmatter block lists exist in the vault today (`grep -rlE '^[ \t]+- ' Isopoda` → 0), so this
is **latent** — but `distribution:`, `habitat:` and `sources:` are list-shaped fields sitting blank
in 11,435 notes, `habitat_stratum` already uses `/`-joined multi-values, and the README explicitly
invites hand-editing. This will fire.

Refuse to touch a key whose value is a block, rather than trying to rewrite it:

```python
BLOCK = re.compile(r"^(%s):[ \t]*$\n(?=[ \t]+\S)", re.M)   # blank header + indented continuation

def _is_block(fm, k):
    return BLOCK.search(fm.replace("%s", k)) is not None    # or build per-key, see below
```

and gate both writers on it — skip the key and (worth it at this scale) log the path, so a field
that silently declined to update is visible rather than mysterious.

### 5. High — `quote()` emits invalid YAML and wrong types

```python
def quote(v):
    return ('"%s"' % v) if re.search(r'[:#\[\],]', str(v)) else str(v)
```

Two gaps: it wraps in `"` without escaping an embedded `"`, and its trigger class misses several
YAML metacharacters. Round-tripped through `yaml.safe_load`:

| input | emitted | parses as |
|---|---|---|
| `stratum:"EN"` | `"stratum:"EN""` | **ParserError** |
| `*star` | `*star` | **ComposerError** (alias) |
| `- lead` | `- lead` | **ScannerError** |
| `yes` | `yes` | `True` — a bool, not the string |
| `He said "hi"` | `He said "hi"` | ok (by luck — no trigger char) |

**You already have the correct implementation in this repo.** `generate.py:39` `emit_val`:

```python
if re.search(r'[:#\[\]{}",]', s) or s != s.strip():
    return '"%s"' % s.replace('"', '\\"')
```

It escapes the embedded quote, covers `{}`, and catches leading/trailing whitespace. And
`generate.py:142` `_set_or_add` independently avoids **both** §3 and §4:

```python
return re.sub(r"^(%s:)[ \t]*$" % re.escape(key),          # ^...$ — blank fields ONLY, so a
              lambda m: "%s %s" % (m.group(1), val),      # populated or block value can't be hit
              fm, count=1, flags=re.M)                    # lambda — replacement never re-scanned
```

So `atlas.py`'s `quote` / `set_fields` / `scaffold_fields` are a strictly worse reimplementation of
machinery that already exists, correct, 100 lines away. **This is the single highest-leverage
change in the review:** extract `emit_val`, `split_note`, `_set_or_add` into `scripts/_vault.py`,
import them in `atlas.py` and `taxonomy.py`, and delete the copies. §3, §4 and §5 all disappear
together, and `safe()` (currently defined identically in three files) goes with them.

Two small hardenings for the shared `emit_val` while it's being moved: also quote a leading
`*&!%@\`` or `- `, and quote the `yes/no/true/false/on/off/null/~` lookalikes so a `common_name: no`
stays a string.

### 9. Medium — `isopoda_index.py` churns 12 notes on every run

```python
today = datetime.datetime.now().strftime("%Y-%m-%d")
...
generated: {today}
```

...then writes unconditionally, with no compare-before-write. Every invocation produces a new diff
on all 12 index notes even when the taxonomy is byte-identical. The README states the pipeline is
"idempotent — re-running changes nothing unless inputs change"; this is the one script that breaks
that promise outright.

`atlas.py` has the mirror-image problem in `GEN = "2026-07-25"` — hardcoded, so it goes stale
silently instead of churning.

Both want the same treatment the writers already use — derive the stamp from the *inputs*, not the
clock, and guard the write:

```python
def write_if_changed(path, text):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            if f.read() == text:
                return False
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return True
```

Use it for every generated note in `isopoda_index.py`, `atlas.py`'s facet maps, `Patterns.md` and
the hub. It also gives you a real changed-file count to print instead of `scaffolded += 1`, which
currently counts *files visited* (§10).

### 11. Medium (latent) — the `realm` regex reads across the newline

`atlas.py:227`:

```python
m = re.search(r"^realm:\s*([a-zA-Z]+)", t, re.M)
```

`\s` includes `\n`, so on a blank `realm:` the match runs into the next key:

```
realm:                  ->  captured realm = 'gbif'      (from the following gbif_id: line)
gbif_id: 42
realm: "marine"         ->  captured realm = None        -> silent fallback to "terrestrial"
```

All 11,435 species notes currently carry an unquoted, non-blank realm (6,392 marine / 4,227
terrestrial / 827 freshwater), so neither branch fires today — **latent**. But blanking one realm
by hand injects a junk category straight into `Maps/By Realm.md`, and quoting one silently
misfiles it as terrestrial. Also note the search runs over the whole document, body included, and
the `"realm:" not in t` guard on line 234 is a plain substring test that would match `realm:`
inside prose.

```python
m = re.search(r"^realm:[ \t]*\"?([A-Za-z]+)", fm, re.M)   # fm, not t; [ \t] not \s; tolerate quotes
```

---

## §3 — GBIF API handling (focus area 3)

This is the weakest part of the expansion. Answering your question directly: **no, not robustly
enough** — but the fix makes it smaller and faster rather than more complicated.

### 6. Medium — 1,138 sequential requests for work GBIF serves in 12

Computed from the tree the crawl actually produced (104 families / 1,030 genera / 7,209 species):

```
order pages        4
family pages     104     children of each family
genus pages    1,030     children of each genus   <-- one request per genus
TOTAL          1,138     sequential, no connection reuse, no delay between requests
               ~21 min wall clock at the 1.1 s/request I measured today
```

Three things make that number bigger than it needs to be:

1. **`limit = 200` when GBIF honours 1,000.** Measured against the order node just now:
   `children?limit=200` → 200 results, `endOfRecords=False`; `children?limit=1000` → all 412 in a
   single call. Raising the page size cuts multi-page taxa outright.
2. **`urllib.request.urlopen` pools nothing** — 1,138 fresh TCP + TLS handshakes. Any pooled
   client (`requests.Session`, `urllib3.PoolManager`, `httpx.Client`) reuses one connection.
3. **The per-genus fan-out is avoidable entirely.** The search endpoint returns the whole order,
   already filtered, with the family and genus on each record:

```
/species/search?datasetKey=<backbone>&higherTaxonKey=643&rank=SPECIES&status=ACCEPTED&limit=1000
```

Measured end to end today: **11,494 accepted species in 12 requests / 117 s** — 95× fewer
requests than the current design, and it needs no suborder/family/genus recursion at all, just a
group-by on the `family`/`genus` fields each record already carries. One caveat I hit: deep offset
paging degrades sharply (pages at offset 0–9,000 took 1.3–1.6 s each; offset 10,000 and 11,000
took 56 s and 45 s). At ~11.5k records that's fine; if the order ever outgrows ~50k, switch to
keyed pagination over families.

Also, on politeness — GBIF advertises no rate-limit headers (I checked; none present), which makes
client-side restraint your responsibility, and there is currently none: no delay between requests,
and a `User-Agent: Mozilla/5.0` that misrepresents a bulk crawler as a browser. Send something
attributable and add a small floor:

```python
UA = "isopod-research/1.0 (+https://github.com/bbeierle12/isopod-research)"
```

### 7. Medium — a failed fetch is indistinguishable from end-of-data, and the damage is permanent

```python
def get_json(url):
    for _ in range(5):
        try:    ...
        except Exception:
            time.sleep(2)
    return None                       # <- exhausted retries

def fetch_children(key, rank):
    ...
    data = get_json(url)
    if not data or not data.get("results"):
        break                         # <- treats "5 failures" as "no more records"
```

After five failures `fetch_children` returns **the partial list it happened to collect** and the
caller cannot tell. The consequences compound:

- A genus whose fetch fails yields zero species and the per-family log line still prints as a
  success: `[57/104] Sphaeromatidae genera=38 species=NNN`. Nothing marks the run as incomplete.
- The exists-check idempotency (`if not os.path.exists(path)`) means **a re-run never repairs it** —
  the missing notes were never created, so nothing signals they're absent. A transient 503 during
  the original crawl is silently permanent.
- `except Exception` also swallows programming errors (`KeyError`, `json.JSONDecodeError`) as if
  they were network flakes, five times, two seconds apart.

The retry policy itself is thin for 1,138 requests: flat 2 s × 5, no exponential backoff, no
jitter, no `Retry-After` handling, and it retries a permanent 404 exactly as hard as a 503.

Raise instead of returning a sentinel, and let the caller decide:

```python
class FetchError(RuntimeError): pass

def get_json(url, attempts=5):
    for a in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: raise FetchError("404 %s" % url) from e
            if e.code < 500 and e.code != 429: raise FetchError("%d %s" % (e.code, url)) from e
            wait = float(e.headers.get("Retry-After") or 0) or (2 ** a)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            wait = 2 ** a
        if a == attempts - 1:
            raise FetchError("gave up after %d attempts: %s" % (attempts, url))
        time.sleep(wait + random.uniform(0, 0.5))     # jitter
```

...and make the run's exit status honest: count families that raised, print them at the end, and
exit non-zero. A crawl that half-worked should not look like a crawl that worked.

### 8. Medium — the family-first shape structurally cannot reach 49 accepted species

Full diff of the vault against all 11,494 accepted Isopoda species:

```
in GBIF but MISSING from vault : 59
    <no family assigned>        49     <- unreachable by design
    Philosciidae                 5     }
    Armadillidae                 3     } all Oniscidea — outside taxonomy.py's scope,
    Hekelidae                    1     } stragglers in the older curated set
    Ligiidae                     1     }
in vault but NOT accepted      :  0     <- no stale notes; the ACCEPTED filter is working
notes missing a gbif_id        :  0
```

The 49 are accepted species with no family in the backbone (`Anhelkocephalon handlirschi`,
`Crenisopus acinifer`, `Rhacura` spp., …). `fetch_children(643, "FAMILY")` filters the order's
children to rank `FAMILY`, so they can never be reached: of Isopoda's 412 direct children, **154
are FAMILY, 51 are GENUS, and 207 are UNRANKED** — the 51 family-less genera and everything under
the unranked nodes are dropped without a word.

Switching to the search endpoint (§6) fixes this for free, since it enumerates species directly
rather than descending a rank ladder. The 49 then need a placement rule — routing them to the
existing `Isopoda/incertae sedis/` tree is consistent with what's already there. Whatever you
choose, **count and report them**; silent omission is what made this invisible for two commits.

Two smaller notes on the same function:

- `fetch_children` filters children by rank *client-side*, so it downloads all 412 order children
  to keep 154. `children` has no rank parameter, so that's inherent — one more reason to prefer
  `search`, which does.
- `taxonomy.py:63` checks `taxonomicStatus` on species but never on families or genera. 10 of
  Isopoda's direct children are `DOUBTFUL`; any that appear in the map are crawled as if accepted.

---

## §1 — Performance & I/O (focus area 1)

### 12. Low — the honest answer: there is no performance problem here

You asked whether the 11,000-file walk can be optimised. I benchmarked the real tree rather than
guessing. Current pass-2 shape (`os.walk`, read in the loop, read again inside `scaffold_fields`,
plus two `os.path.exists` guards) against a single-read `os.scandir` version:

```
A  current   (walk + 2 reads + 2 stats/file)    0.58 s   11,435 files
B  optimised (scandir + 1 read/file)            0.35 s   11,435 files
```

**0.23 s.** Restructuring this for speed is not worth doing, and I'd rather tell you that than
hand you a micro-optimisation. Two caveats that do make the change worthwhile, for other reasons:

- **Syscall count, not seconds, is the portable metric.** Current: 22,870 `open`s (two reads per
  note) plus 11,435–22,870 `stat`s from the `os.path.exists` guards at the top of each writer.
  Optimised: 11,435 `open`s and no `stat`s at all — the guards go away with the single read, and
  `os.scandir` already carries the entry type so filtering costs nothing. On Linux with a warm
  page cache that halving is invisible; on `C:\Users\...` with Defender real-time scanning and
  possibly OneDrive in the path, per-`open` cost is an order of magnitude higher and the same
  halving is real. I can't measure your machine from here — but the fix is free, so the asymmetry
  doesn't matter.
- **It removes the triple-read as a *correctness* hazard.** Right now the loop reads `t`, then
  `scaffold_fields` re-reads and may write, then the `if "realm:" not in t` test consults the
  **stale** `t` from before that write, and `set_fields` re-reads a third time. It happens to be
  benign (the two functions touch disjoint keys) but it is a read-modify-write race with itself,
  and it's why the write-count reporting is wrong.

Read once, transform in memory, write once:

```python
def visit(path):
    with open(path, encoding="utf-8", newline="") as f:      # newline="" — see §5.3
        t = f.read()
    m = FM.match(t)
    if not m:
        return None, False
    fm = m.group(2)
    fm = scaffold(fm, vals)          # pure string -> string
    fm = ensure_realm(fm, realm)     # pure string -> string
    new = m.group(1) + fm + m.group(3) + m.group(4)
    if new == t:
        return realm, False
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    os.replace(tmp, path)            # atomic
    return realm, True
```

Making the writers pure `str -> str` is what buys the single read; the atomic swap is §5.4.

For the traversal itself, `Path.rglob("*.md")` reads better than the manual `os.walk` + `join`
gymnastics, and prunes nothing you need:

```python
for p in (VAULT / "Isopoda").rglob("*.md"):
    if p.name.startswith("_"):
        continue
```

### 13. Low — `taxonomy.py` calls `os.makedirs` once per species

`taxonomy.py:73` runs inside the species loop, so it fires 11,435 times to create 1,597
directories — `exist_ok=True` makes the redundant 9,838 calls harmless but not free. Hoist it to
the genus loop, where the directory is actually determined.

Same shape in `atlas.py`: `if not os.path.exists(path): return` at the top of both writers,
immediately followed by `open()`. That's a redundant stat *and* a TOCTOU window. `try: ... except
FileNotFoundError: return` does the job in one syscall.

---

## §4/§5 — Structure, readability, idiomatic Python (focus area 4)

### 10. Medium — generated counts are wrong, one of them visibly

`Maps/By Realm.md`, line 10, as currently committed:

> **11448 of 11435 Isopoda species classified.**

`rrows` used to hold only classified species, and the map header still describes it that way. Pass 2
now appends **every** species (`atlas.py:241`), then 13 provisional hobby forms are appended on top,
so `len(rrows)` = 11,448 while the denominator `NT` = `len(tax_species)` = 11,435. The comment at
`atlas.py:240` is the moment the invariant broke, written down in the file:

```python
# We need to map all species in By Realm, not just those with research entries! Wait, By Realm
# uses rrows. If e is None, it wasn't added to rrows. So we must append it.
```

That reasoning is right, but `rrows` was doing double duty as "rows to render" *and* "the count of
classified species", and only the first use got updated. It propagates: the hub's "populated only
where studied (%d so far, evidence-graded a/b/c)" and `Patterns.md`'s "%d Oniscidea species
classified so far" both now report **11,448 studied species** against the 24 entries actually in
`data/ecology.json` (the README says ~33 — worth reconciling separately). Split the two
concepts — `rrows` for rendering, `sum(1 for r in rrows if r["ecomorph"] or r["trophic"] or ...)`
for the count — and drop the dead `if e:` / `else:` at `atlas.py:237-241`, whose branches are
identical (`e` is already `None` in the else).

Related count problems:

- `_Isopoda Index.md` reports `family_count: 154`, but only **146** families have a directory.
  `isopoda_index.py:53` takes `len(sub_families)` from the *map*, not from what's on disk. The
  result is **11 family rows reporting `| 0 | 0 |`** — 8 with no directory at all (`Archeoniscidae`,
  `Armadilliidae`, `Atlantidiidae`, `Chaetilidae`, `Gnathidae`, `Hekelidae`, `Parasellidae`,
  `Phreatoicopsididae`) and 3 with an empty directory (`Periscyphicidae`, `Pseudarmadillidae`,
  `Sphaeroniscidae`) — each linking to an index note that will never exist. Count what you
  generated, and either drop the empty rows or mark them explicitly as "no accepted species in
  GBIF".
- `scaffolded` counts files *visited*, not files *changed* (§9 gives you the real number).

### 5.1 — Documentation drift after the expansion

`atlas.py` is still written as an Oniscidea tool while doing order-wide work. Its module docstring
("facet & pattern cross-reference over the whole **Oniscidea** taxonomy", "apply to ALL Oniscidea
species"), the pass-2 section header, the hub's "Research axes <small>(all Oniscidea)</small>", the
`Patterns.md` scope note, and the footer link `[[_Oniscidea Index|Oniscidea taxonomy (4,226
species)]]` all describe the pre-expansion scope. A reader can't tell which statements are stale
and which are deliberate scoping (the husbandry facets genuinely *are* still Oniscidea-only, which
is what makes the drift actively confusing).

`built[8:]` / `built[:8]` at `atlas.py:333-336` is the same fragility in code form: the split
between husbandry and research maps is a magic index that silently mis-slices if anyone inserts a
map. Tag each entry (`built.append((title, fname, n, "research"))`) and filter.

### 5.2 — `VAULT` is hardcoded seven times, and one copy points somewhere else

```
scripts/atlas.py:17          VAULT = r"C:\Users\Bbeie\isopod-research"
scripts/generate.py:14       VAULT = r"C:\Users\Bbeie\isopod-research"
scripts/husbandry.py:11      VAULT = r"C:\Users\Bbeie\isopod-research"
scripts/isopoda_index.py:3   VAULT = r"C:\Users\Bbeie\isopod-research"
scripts/taxonomy.py:3        VAULT = r"C:\Users\Bbeie\isopod-research"
scripts/validate.py:16       VAULT = r"C:\Users\Bbeie\isopod-research"
scripts/seed.py:8            VAULT = r"C:\Users\Bbeie\Downloads\Insect and Reptile research"   <-- different!
```

No script in the pipeline runs anywhere but that one Windows account, and `seed.py` has already
drifted to a stale directory. Every script lives in `scripts/` inside the vault, so the path is
derivable:

```python
# scripts/_vault.py
from pathlib import Path
VAULT = Path(__file__).resolve().parent.parent
ISOPODA, MAPS, DATA = VAULT / "Isopoda", VAULT / "Maps", VAULT / "data"
```

With an env override (`os.environ.get("ISOPOD_VAULT")`) for anyone running against a copy. This is
the natural home for the shared `emit_val` / `split_note` / `_set_or_add` / `safe` from §5.

### 5.3 — Line endings: the `\r?\n` in the regexes is dead code

`.gitattributes` declares `*.md text eol=lf`, so the working tree is LF even on Windows. Both
writers open in **text mode**, which converts CRLF→LF on read — so `\r` never reaches the regex and
every `\r?\n` alternative is unreachable. Worse, text-mode *writing* on Windows converts LF→CRLF,
so `atlas.py` rewrites LF notes as CRLF; git normalises them back on commit, which is why this has
been invisible. Pass `newline=""` on read and `newline="\n"` on write to make the bytes match the
declared intent, then the `\r?` can go.

### 5.4 — Writes are not atomic

Both writers do `open(path, "w")` then `write()`. An exception mid-loop (§3 will produce one) or a
Ctrl-C leaves a **truncated** note — for a vault that is the source of truth, across 11,435 files.
`write to path + ".tmp"` then `os.replace()` makes each note all-or-nothing; `os.replace` is atomic
on both POSIX and Windows.

### 5.5 — `atlas.py` is a script with no seams

Everything from line 168 down runs at import: file loads, both passes, all writes. There's no
`main()`, so it can't be imported, tested, or partially run — and no `--dry-run`, which is what you
actually want before letting a regex loose on 11,435 tracked files. Wrapping the two passes in
functions behind `if __name__ == "__main__":` with `argparse` (`--dry-run`, `--only oniscidea`,
`--verbose`) costs little and would have surfaced §3, §4 and §10 before they were committed.

While you're in there: `import os, re, json` on one line and the `with open(...) as f: t = f.read()`
one-liners are both PEP 8 violations that make the writers harder to scan than they need to be —
and these two functions are exactly the ones that turned out to be subtly wrong.

### 5.6 — Smaller items

- **`taxonomy.py:58`** — `gen_data["canonicalName"] or gen_data["scientificName"]` uses `[]` where
  the species branch correctly uses `.get()`. `KeyError` if GBIF omits the key; `.get()` for both.
- **Trailing whitespace in 4,226 notes.** `"%s: %s\n" % (k, quote(v) if v else "")` emits
  `ecomorph: ` with a trailing space when the value is blank. Confirmed: 4,226 notes currently carry
  such lines (the Oniscidea set, where `atlas.py` inserted the fields). Harmless to YAML, but it
  will fight any whitespace-stripping editor setting or pre-commit hook into a permanent
  rewrite/re-strip loop — an idempotency break introduced from outside. Emit `"%s:\n" % k` when
  blank.
- **Empty frontmatter is silently skipped.** `^(---\r?\n)(.*?\r?\n)(---\r?\n)(.*)$` cannot match
  `---\n---\n` (group 2 requires at least one line), so such a note is skipped with no diagnostic —
  as is any note whose frontmatter is malformed. Both writers `return` on no-match. Count and report
  the skips; silent no-ops over 11,435 files are how §8 stayed hidden.
- **`safe()` is Windows-incomplete.** It strips `\/:*?"<>|` but not the reserved device names
  (`CON`, `PRN`, `AUX`, `NUL`, `COM1`…), trailing dots/spaces, or case-insensitive collisions. Two
  taxa differing only in case or punctuation silently overwrite each other on Windows and macOS.
  Low probability with binomial names; cheap to assert against.
- **`scratchpad.log` is tracked in git** at the vault root, so Obsidian indexes it as vault content
  and every crawl appends to a tracked file. Move it to `logs/` (gitignored) and use `logging`
  rather than hand-rolled `print` + `open(..., "a")` in the loop — you get levels, timestamps and
  a `--verbose` flag for free.
- **`taxonomy.py` has no refresh path.** `if not os.path.exists(path)` gives you resumability, but
  it also means a template change never reaches the 11,435 existing notes, and a note written by a
  partially-failed run stays wrong forever. A `--refresh` flag that re-renders managed frontmatter
  keys while preserving hand-edited ones is the missing half — and `generate.py`'s
  `upsert`/`build_frontmatter` (`MANAGED` vs `preserved`) is already the pattern for it.
- **README pipeline is incomplete.** `scripts/taxonomy.py` and `scripts/isopoda_index.py` aren't in
  the documented `seed → validate → husbandry → generate → atlas` sequence, so there's no recorded
  way to reproduce the expansion.

---

## Suggested order of work

1. **§1** — make `taxonomy.py` compile on 3.9+ (`json.dumps` for authorship). One line.
2. **§2** — emit family and genus index notes in `isopoda_index.py`. Fixes 14,530 broken links; the
   data is already in scope.
3. **§5** — extract `scripts/_vault.py` (`VAULT`, `safe`, `emit_val`, `split_note`, `_set_or_add`,
   `write_if_changed`); delete `atlas.py`'s `quote`/`set_fields`/`scaffold_fields`. Clears §3, §4,
   §5, §5.2 and half of §12 in one change.
4. **§10 / §9** — fix the counts, make the writes conditional, drop the dead branch.
5. **§6 / §7 / §8** — rewrite the crawler around `/species/search` with a pooled session, honest
   errors and a non-zero exit on partial failure. 1,138 requests → 12, and the 49 unplaced species
   become reachable.
6. **§12 / §5.3 / §5.4 / §5.5** — single-read pass, `newline=` handling, atomic writes, `main()` +
   `--dry-run`.

Steps 1–4 are small and remove every confirmed defect. Step 5 is the real rewrite and is where the
crawler stops being fragile.
