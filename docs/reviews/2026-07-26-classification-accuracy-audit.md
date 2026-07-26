# Classification accuracy audit — Isopoda taxonomy, realms & ecology axes

**Scope:** `data/isopoda_suborders.json` (154 families → suborder + realm), `data/ecology.json`
(24 research entries), the derived `suborder`/`realm` frontmatter on 11,435 species notes, and the
classifier functions in `scripts/atlas.py` that turn those values into `Maps/`.
**Reviewed:** 2026-07-26 · vault at `b8c80cf`
**Authorities used:** WoRMS — the *World List of Marine, Freshwater and Terrestrial Isopod
Crustaceans* (the global taxonomic authority for Isopoda, and the source `isopoda_suborders.json`
itself cites) — and the GBIF Backbone Taxonomy, queried live. Every finding below was checked
against one or both; nothing here is asserted from memory.

---

## Summary

Two things are genuinely solid, and worth saying before the errors:

- **The vault is perfectly self-consistent.** All 11,435 species notes have `suborder`, `family`,
  `genus` and `scientificName` frontmatter that matches their directory path exactly — **0
  mismatches**. Nothing is filed in a folder that disagrees with its own metadata.
- **Where `ecology.json` is well-grounded, it is genuinely accurate.** *Hemilepistus reaumuri*
  (subsocial, monogamous, biparental), *Armadillidium vulgare* (Wolbachia/f-element feminization),
  *Trichorhina tomentosa* (obligate all-female parthenogenesis), *Tylos punctatus* (supralittoral,
  beach-cast algae, LI), *Atlantoscia floridana* (iteroparous) are all correct, and the a/b/c
  evidence grading is a good design that repeatedly saved the weaker calls from overclaiming.

The errors below are real, and several are visible in the published `Maps/`.

| # | Severity | Finding | Notes affected |
|---|---|---|---|
| A1 | **Critical** | Suborder **Epicaridea** is missing; its 17 families are filed elsewhere | 891 |
| A2 | **Critical** | 12 families carry a realm that contradicts WoRMS | 213 |
| A3 | **Critical** | `norm_repro` files two explicitly-sexual species as *Parthenogenetic* | 2 (published) |
| A4 | **Critical** | "incertae sedis" is a fossil dumping ground with a guessed `realm: marine` | 29 |
| A5 | High | An extant freshwater troglobite filed as marine / incertae sedis | 1 |
| A6 | High | `_Asellota Index.md` declares "Realm: marine" for a suborder that is 1/3 freshwater | index |
| B1 | High | Family-level realm is too coarse for 25 families; 3 realm buckets can never fill | ~2,000 |
| B2 | High | Terrestrial-only research axes applied order-wide; the guilds the expansion made relevant have no data path | 7,209 |
| B3 | High | ~5% of the vault's species are not accepted in WoRMS (GBIF-only taxonomy) | sampled |
| C1–C7 | Medium | Individual `ecology.json` entries to re-check | 24 |
| D1–D4 | Medium | Biogeographic classifiers have systematic holes | 3 of 112 |

---

## A1 — Critical: suborder **Epicaridea** is missing; 891 species notes are in the wrong suborder

I asked WoRMS directly for the accepted suborders of Isopoda (`AphiaChildrenByAphiaID/1131`):

```
Asellota · Calabozoidea · Cymothoida · Epicaridea · Limnoriidea · Oniscidea
Phoratopidea · Phreatoicidea · Sphaeromatidea · Tainisopidea · Valvifera      = 11 accepted
```

The vault also has 11 "suborders" — but they are **not the same 11**. It omits **Epicaridea** and
counts **`incertae sedis`** as a suborder. (WoRMS does carry an `Isopoda incertae sedis` node, but
its status is *temporary name*, not Suborder.) So the README's "11 suborders · 154 families" is the
right *number* and the wrong *set*.

17 families that WoRMS places in Epicaridea are filed elsewhere in the vault:

| filed as | families | species notes |
|---|---|---|
| Cymothoida | Bopyridae (669), Dajidae (66), Entoniscidae (43), Cabiropidae (34), Cryptoniscidae (30), Hemioniscidae (8), Cyproniscidae (7), Ionidae (7), + Asconiscidae, Capitoniscidae, Crinoniscidae, Cumoechidae, Entophilidae, Microniscidae, Podasconidae, Cryptothiridae | 889 |
| **Oniscidea** | **Stellatoniscidae** | **2** |

**Two different problems here, and they need different verdicts:**

1. **Cymothoida for the epicarideans is a defensible published position, not an error.** Brandt &
   Poore (2003) placed Epicaridea *within* Cymothoida, and plenty of literature still follows that.
   But `isopoda_suborders.json` opens with `"_source": "Suborders per WoRMS"`, and WoRMS does not.
   Either the data is stale against its stated authority or the source note is wrong — pick one and
   record the decision, because right now the file documents an authority it doesn't follow.

2. **Stellatoniscidae in Oniscidea is an unambiguous error under either scheme.** Stellatoniscidae
   is a cryptoniscoid epicaridean — a marine parasite. It is currently filed in the terrestrial
   woodlouse suborder with `realm: terrestrial`. WoRMS: suborder Epicaridea, `isMarine=1`.

**One thing that looks like an omission but is correct:** Microcerberidae is filed under Asellota,
and there is no Microcerberidea suborder. I checked — WoRMS lists **Microcerberidea as a junior
subjective synonym**, so folding it into Asellota is right. Don't "fix" that.

---

## A2 — Critical: 12 families carry a realm that contradicts WoRMS (213 species notes)

Compared each family's assigned realm against WoRMS `isMarine`/`isBrackish`/`isFreshwater`/
`isTerrestrial` flags. 102 of 139 checkable families matched exactly. These 12 did not:

| family | notes | vault says | WoRMS | direction |
|---|---|---|---|---|
| Stenetriidae | 87 | freshwater | **marine** | marine mislabelled fresh |
| Lepidocharontidae | 73 | freshwater | **marine** | " |
| Gnathostenetroididae | 21 | freshwater | **marine** | " |
| Pseudojaniridae | 7 | freshwater | **marine** | " |
| Urstylidae | 4 | freshwater | **marine** | " |
| Vermectiadidae | 2 | freshwater | **marine** | " |
| Mictosomatidae | 1 | freshwater | **marine** | " |
| Microparasellidae | 13 | marine | **freshwater** | genuinely mixed, see below |
| Irmaosidae | 2 | marine | **terrestrial** | terrestrial mislabelled marine |
| Stellatoniscidae | 2 | terrestrial | **marine** | marine mislabelled terrestrial |
| Brasileirinidae | 1 | terrestrial | **freshwater** | + suborder also wrong (→ Calabozoidea) |
| Atlantidiidae | 0 | marine | **terrestrial** | junior synonym of Porcellionidae |

**8 of the 12 are Asellota**, and 195 of the 213 notes are marine asellotes labelled *freshwater*.
I verified the four largest at **species** level rather than trusting the family flag:

```
Stenetriidae         Hansenium antillense, H. caicoensis, H. chiltoni        -> WoRMS marine
Lepidocharontidae    Janinella brasiliensis, J. renaudae,
                     Lepidocharon lizardensis, L. priapus                    -> WoRMS marine (all accepted)
Gnathostenetroididae Caecostenetroides ascensionis, ischitanum,
                     leptosoma, mooreus                                      -> WoRMS marine
```

The Lepidocharontidae/Microparasellidae pair shows what went wrong. These are the two interstitial
asellote families and they split on habitat: **Lepidocharontidae are marine psammic**,
**Microparasellidae (*Microcharon*, *Angeliera*) are freshwater/groundwater stygobites**. The map
has **both backwards**. That is the signature of a plausible guess from the family name rather than
a lookup — "interstitial, obscure, probably groundwater" for one and the reverse for the other.

**Microparasellidae deserves a more honest answer than a flip.** At species level it is genuinely
mixed — *Angeliera cosettae* is freshwater, *A. dubitans* and *A. gracilis* are marine. No single
family-level realm is correct. See B1.

---

## A3 — Critical: `norm_repro` files two explicitly-sexual species under *Parthenogenetic*

`atlas.py:116` classifies reproduction by substring:

```python
def norm_repro(v):
    v = (v or "").lower()
    if "parthenogen" in v: return "Parthenogenetic"
```

`"parthenogen"` matches inside a **negation** and inside a **hedge**. From the published
`Maps/By Reproduction.md`, verbatim:

```
## Parthenogenetic  <small>(4)</small>

| [[Armadillidium nasatum]]        | Armadillidiidae | sexual (NOT parthenogenetic)        | a/b |
| [[Platyarthrus hoffmannseggii]]  | Platyarthridae  | sexual (parthenogenesis suspected)  | b/c |
| [[Trichoniscus pusillus]]        | Trichoniscidae  | parthenogenetic triploid + sexual diploid | a |
| [[Trichorhina tomentosa]]        | Platyarthridae  | obligate parthenogenesis (all-female)     | a |
```

Half that table is wrong, and the table prints its own contradiction — the Detail column says
"NOT parthenogenetic" while the heading says Parthenogenetic. *A. nasatum* is sexual; the
`ecology.json` author wrote "(NOT parthenogenetic)" **specifically to record that**, and the
normaliser inverted it. *P. hoffmannseggii* is recorded as sexual with parthenogenesis merely
suspected (evidence `b/c`) and is presented as confirmed.

Classify from a controlled vocabulary instead of prose. `ecology.json` should carry
`reproduction_mode: sexual | sexual_assumed | parthenogenetic | parthenogenetic_obligate |
mixed_parthenogenetic_sexual | subsocial_biparental` as a **separate field** from the free-text
note, and `norm_repro` should read the field and never parse the note. If substring matching must
survive, at minimum guard the negation and the hedge — but the enum is the real fix, and the same
argument applies to `norm_trophic`.

**`norm_trophic` is clean, and I verified it:** all 24 entries map to the intended bucket, including
the order-dependent ones ("General detritivore (+facultative herbivore)" → *Detritivore
(+herbivore)*, "Coprophage/detritivore (ant nests)" → *Detritivore/coprophage*). No trophic
misclassification exists today — but it is one hedged phrase away from the same failure, e.g. an
entry reading "not a wood-borer" or "algivore not confirmed".

---

## A4 — Critical: "incertae sedis" is a fossil dumping ground with a guessed realm

All 29 species notes under `Isopoda/incertae sedis/` carry `realm: marine`, and **26 of them are
fossil taxa**:

```
Archaeoniscidae  9  Archaeoniscus (brodiei, edwardsii, texanus, coreaensis, italiensis,
                    aranguthyorum), Codoisopus brejensis, Ferreniscus magransi, F. yamadai
Urdidae         10  Urda (buechneri, cretacea, mccoyi, moravica, rostrata, stemmerbergensis,
                    suevica, zelandica), Protourda circunscriptia, P. tupiensis
Palaeophreatoicidae 3 Palaeophreatoicus sojanensis, Palaeocrangon problematicus, Hesslerella shermani
Schweglerellidae 1  Lantoceramiidae 1  Tricarinidae 1
```

None has a WoRMS record — as expected for palaeontological taxa. Three consequences:

1. **There is no `extinct` flag anywhere in the schema.** 26 fossil species sit in an atlas of
   living-isopod ecology carrying a modern `realm`, and they are counted in every "of 11,435 Isopoda
   species" denominator. Add `extinct: true` and exclude them from the ecology axes by default.
2. **`Palaeophreatoicidae` → `marine` is wrong.** Palaeophreatoicideans are Permian **freshwater**
   phreatoicideans — the group's whole significance is that Phreatoicidea has been freshwater since
   the Palaeozoic. Suborder should be Phreatoicidea, realm freshwater.
3. **Fossils are not confined to this tree.** *Eostenetrium guerangeri* sits in Stenetriidae, for
   example. Do not assume "incertae sedis" == "fossil" and call it handled.

### Six of the 16 "incertae sedis" families are misspelling-duplicates of families already in the map

Every bogus twin landed in `incertae sedis / marine`, while the correct spelling is correctly placed
elsewhere in the same file:

| bogus entry (incertae sedis / marine) | correct entry already in map | WoRMS on the correct name |
|---|---|---|
| `Amphisopodidae` | `Amphisopidae` → Phreatoicidea / freshwater | accepted, **freshwater** |
| `Archeoniscidae` | `Archaeoniscidae` | (fossil; not in WoRMS) |
| `Armadilliidae` | `Armadillidiidae` / `Armadillidae` → Oniscidea / terrestrial | accepted, **terrestrial** |
| `Chaetilidae` | `Chaetiliidae` → Valvifera / marine | accepted, marine |
| `Gnathidae` | `Gnathiidae` → Cymothoida / marine | accepted, marine+brackish |
| `Phreatoicopsididae` | `Phreatoicopsidae` → Phreatoicidea / freshwater | accepted, **freshwater** |

So `Amphisopodidae`, `Armadilliidae` and `Phreatoicopsididae` are labelled **marine** when the
family they duplicate is freshwater or terrestrial. All 15 of these names *are* accepted
FAMILY-rank nodes in the GBIF backbone, so they aren't curator typos — they are GBIF backbone
artifacts that the map then had to invent a realm for. That is exactly why they should be resolved
against WoRMS and merged, not bucketed.

**A caution on de-duplicating by name similarity:** several near-identical pairs are genuinely
distinct valid families and must not be merged. I checked these in WoRMS — `Arcturidae` **and**
`Arcturididae` are both accepted; so are `Armadillidae` and `Armadillidiidae`, `Anthuridae` and
`Antheluridae`, `Alloniscidae` and `Balloniscidae`, `Cryptoniscidae` and `Cyproniscidae`,
`Amphisopidae` and `Mesamphisopidae`, `Phreatoicidae` and `Phreatoicopsidae`. Resolve by AphiaID,
never by string distance.

### The rest of the bucket has a determinable placement

| entry | notes | WoRMS says |
|---|---|---|
| `Atlantidiidae` | 0 | junior subjective synonym of **Porcellionidae** — Oniscidea, terrestrial |
| `Parasellidae` | 0 | unavailable name for **Janiridae** — Asellota, marine (Janiridae is already in the map) |
| `Cryptothiridae` | 1 | **Epicaridea**, marine (taxon inquirendum) |
| `Irmaosidae` | 2 | **Oniscidea**, **terrestrial** (unavailable name) |
| `Microniscidae` (filed Cymothoida) | 0 | unaccepted → "Bopyroidea incertae sedis" — a larval-form name, not a family |
| `Buddelundiellidae` (filed Oniscidea) | — | **superseded rank** → valid as subfamily **Buddelundiellinae** |

Three names in the map have no WoRMS record and I could not verify them either way:
`Periscyphicidae`, `Pseudarmadillidae`, `Sphaeroniscidae` (all Oniscidea / terrestrial in the map,
0 species notes each). The placement is plausible from the literature; flag them as unverified
rather than assume.

---

## A5 — High: an extant freshwater troglobite filed as marine

`Isopoda/incertae sedis/Amphisopodidae/Lakeamphisopus/Lakeamphisopus trogloendemicus.md`

*Lakeamphisopus* is an **extant Australian phreatoicidean** — a subterranean **freshwater**
troglobite (Amphisopidae). It is currently `suborder: incertae sedis`, `realm: marine`. It should be
Phreatoicidea / freshwater. It is here only because its family was spelled `Amphisopodidae`, so
it inherited the bucket's blanket marine label (A4).

## A6 — High: `_Asellota Index.md` declares "Realm: marine" for a suborder that is one-third freshwater

`isopoda_index.py:16` sets the suborder's realm from whichever family it encounters **first**:

```python
if sub not in suborder_info:
    suborder_info[sub] = {"realm": info["realm"], "families": {}}
```

Asellota is the one mixed suborder in the map — 22 marine families, 12 freshwater — and the first
family alphabetically is Acanthaspidiidae (marine). So the published index reads
**"Realm: marine"** for the suborder that contains Asellidae and Stenasellidae, the textbook
freshwater and groundwater asellotes. Every other suborder happens to be single-realm, which is why
this went unnoticed. Emit the set (`marine, freshwater`), or omit the field when it isn't uniform.

---

## B1 — High: family-level realm is too coarse for 25 families, and 3 realm buckets can never fill

WoRMS lists multiple environments for 25 of the mapped families where the vault records one:

| vault says | WoRMS | families |
|---|---|---|
| terrestrial | marine + brackish + terrestrial | **Ligiidae** |
| terrestrial | marine + freshwater + terrestrial | Scyphacidae |
| terrestrial | freshwater + terrestrial | Styloniscidae, Trichoniscidae, Olibrinidae |
| marine | marine + brackish + freshwater | Cirolanidae, Cymothoidae, Aegidae, Anthuridae, Sphaeromatidae, Nannoniscidae |
| marine | marine + freshwater | Bopyridae, Corallanidae, Entoniscidae, Idoteidae, Ionidae, Janiridae, Paramunnidae, Paranthuridae |
| marine | marine + brackish | Gnathiidae, Limnoriidae |
| freshwater | brackish + freshwater | Asellidae |
| freshwater | marine + brackish + freshwater | Stenasellidae |
| freshwater | marine + freshwater | Microcerberidae, Atlantasellidae |

This is a **schema** problem, not 25 individual mistakes: `realm` is single-valued and drawn from
`marine | freshwater | terrestrial`, so no family can express "marine and freshwater", and the
littoral/brackish/interstitial categories the ecology enum defines can never be produced from the
taxonomy at all. `Maps/By Realm.md` renders buckets for `littoral`, `brackish` and `interstitial`
that are permanently empty.

The sharpest symptom: **`Ligia` is the archetypal littoral isopod**, and the vault's two datasets
disagree about it. `ecology.json` correctly gives `Ligia *` → `terrestrialization: littoral`,
`stratum: LI`; the family map gives Ligiidae → `realm: terrestrial`. Same animal, two files, two
answers. Same for Tylidae (*Tylos punctatus* is `littoral`/`LI` in `ecology.json`, `terrestrial` by
family).

Make `realm` a list (`realm: [marine, freshwater]`), populate it from WoRMS flags per family, and
let species-level entries override. Then `By Realm` can honestly show a species under both.

## B2 — High: terrestrial-only research axes are applied order-wide, and the guilds the expansion made relevant have no data path

All 24 `ecology.json` entries are Oniscidea (plus littoral *Ligia*/*Tylos*/*Deto*). That is not an
oversight to fix by adding rows — **two of the five research axes are terrestrial-isopod concepts
that are not defined for aquatic isopods**:

- **Ecomorph** is Schmalfuss (1984), *Eco-morphological strategies in terrestrial isopods*. Runner /
  Clinger / Roller / Creeper / Spiny are strategies for life on land. There is no meaningful
  Schmalfuss ecomorph for a bopyrid in a shrimp's branchial chamber. The map subtitle does say
  "(terrestrial)" — good — but the header still reports "of 11435 Isopoda species".
- **Terrestrialization** (littoral → hygrophilous → mesophilous → xerophilous) measures independence
  from water. It is undefined for a fully marine asellote, not merely unmeasured.

The current framing counts 7,209 aquatic species as *awaiting study* on axes that will never apply
to them. Scope each axis explicitly (`applies_to: Oniscidea`) and denominate against that scope,
or the "blank until researched" promise quietly becomes "blank forever" for two-thirds of the vault.

Meanwhile the axes that *would* fit the aquatic expansion are the ones with no data and no code
path. Four `trophic` values in the documented enum are **unreachable** — `norm_trophic` has no
branch that returns them and no entry produces them:

| enum value | never assigned | but the vault now contains |
|---|---|---|
| Parasite (ectoparasite) | ✗ | Bopyridae 669, Cymothoidae 411, Dajidae 66, Entoniscidae 43, Cabiropidae 34, Cryptoniscidae 30 = **1,253** obligate parasites |
| Wood-borer | ✗ | Limnoriidae **62** |
| Micropredator/scavenger | ✗ | Cirolanidae 601, Gnathiidae 249, Aegidae 159, Corallanidae 87 = **1,096** |
| Filter/deposit-feeder | ✗ | various Asellota / Sphaeromatidea |

~2,400 species notes whose feeding biology is well established in the literature and already has an
enum slot, with nothing wired up. These are the cheapest, highest-confidence ecology rows available
— family-level assignment for Bopyridae or Limnoriidae is uncontroversial — and would be a better
use of effort than the 25th woodlouse.

## B3 — High: ~5% of the vault's species are not accepted in WoRMS

The taxonomy is GBIF-only while the suborder/realm layer is WoRMS-derived, and the two are never
reconciled. Stratified random sample, 171 notes (up to 20 per suborder directory, seed fixed):

```
accepted in WoRMS        137   80.1%
no WoRMS record           26   15.2%   (mostly the fossil taxa of A4)
NOT accepted in WoRMS      8    4.7%
```

Examples of the 4.7%:

```
Pseudione affinis      superseded combination  -> Cryptione affinis
Parapenaeon tertium    superseded combination  -> Parapenaeonella tertia
Sphaeroma curtum       junior subjective synonym -> Cymodoce truncata
Cymodoce granulata     junior subjective synonym -> Cerceis trispinosa
Onychocepon resupinum  incorrect original spelling -> Onychocepon resupinus
Apophrixus afzali      taxon inquirendum
Stenosoma gracillimum  taxon inquirendum
Alloniscus simplex     uncertain
```

**Read that 4.7% as a sample rate, not a vault count.** The sample is stratified by suborder, not
proportional to size, so scaling it to 11,435 is not valid — the honest statement is that a
non-trivial minority of GBIF-accepted names are synonyms or unresolved under the isopod community's
own register, and the real figure needs a full crossmatch. That crossmatch is cheap: WoRMS
`AphiaRecordsByNames` takes ~40 names per request, so all 11,435 is ~290 requests — about the same
budget the current crawler spends on one run (see the pipeline review, §6).

Recommendation: keep GBIF as the source of the *tree*, and add `worms_aphia_id` +
`worms_status` + `worms_accepted_name` to each species note. For a vault that must be
biologically accurate, "GBIF says accepted" is not the same claim as "the isopod taxonomic community
says accepted", and right now the notes assert the latter while only checking the former.

---

## C — `ecology.json` entries to re-check (24 entries)

The well-sourced entries are listed in the Summary. These need a second look:

- **C1. *Deto echinata* → `Runner`.** The species' diagnostic character is its prominent dorsal
  spines (*echinata* = spiny), and the enum has a `Spiny` value used for *Merulanella*. It is also a
  long-legged wrack runner, so both readings are arguable — but the current call is the one that
  ignores the animal's defining morphology. Evidence is already `b`/`c`; resolve against Schmalfuss.
- **C2. *Trichorhina tomentosa* → `Non-conformist`.** A small, weakly-pigmented endogeic form.
  `Creeper` is the closer Schmalfuss fit; `Non-conformist` is for taxa that defy the scheme.
- **C3. *Cylisticus convexus* → `Roller`.** Usually described as an **imperfect** conglobator (it
  cannot close fully). The husbandry axis already has a `Partial roller` value that would fit; the
  research axis has no equivalent, which may be the real gap.
- **C4. *Trichoniscus pusillus* → "parthenogenetic triploid + sexual diploid".** This reflects the
  older subspecies treatment (*T. pusillus pusillus* / *T. p. provisorius*). Current practice splits
  them: *T. pusillus* is the triploid parthenogen, ***T. provisorius*** the diploid sexual — **and
  the vault already contains `Trichoniscus provisorius` as a separate species note** with no ecology
  entry. So the entry attributes to one species a system that the vault's own taxonomy splits
  across two. Split the entry.
- **C5. `Cubaris *` genus wildcard.** In the hobby "Cubaris" is a wastebasket — most hobby forms
  sold as *Cubaris* belong to *Merulanella*, *Nesodillo* and others. A genus-level ecology row
  therefore attaches `stratum: CA/SA` and "Detritivore + wood/calcium" to a non-monophyletic
  grouping. Also `CA` (cave) is doubtful for genus *Cubaris* generally, even if it fits the
  Thai karst hobby forms. Same concern, milder, for `Merulanella *` → `EP/CA`.
- **C6. Unsourced specifics.** "monolayer marsupial sac" (*Armadillo officinalis*) and "feminizable
  by wVulC" (*Cylisticus convexus*) are precise, checkable claims with no citation — wVulC is the
  *A. vulgare* Wolbachia strain, so cross-species feminization is a specific experimental result
  that should carry a reference. `ecology.json` has no `source` field at all; for a vault that must
  be defensible, per-claim citations matter more than another axis.
- **C7. Free text vs the documented enums.** The `_comment` defines controlled vocabularies, and
  most values don't match them ("General detritivore (+facultative herbivore)" vs
  "Detritivore (+herbivore)"; "sexual (sperm storage)" vs "Sexual"). That mismatch is *why*
  `norm_trophic`/`norm_repro` exist, and A3 is the direct consequence. Store the enum value and the
  prose note in separate fields.

---

## D — Biogeographic classifiers (`atlas.py`)

Ran `region()` and `biome()` over all 112 hobby forms. **3 are currently misfiled**, and the rules
have systematic holes:

- **D1. No South or Central America, and no `california`/`mexico`/`pacific`.** `region()` tests only
  `arizona, usa, americas, florida, caribbean`. ***Tylos punctatus*** — origin "Pacific coast
  (California to Mexico)" — is filed under region **"Other"**. Any Brazilian, Chilean, Peruvian or
  Mexican locality would be too.
- **D2. `"tropics"` is not in the Cosmopolitan/pantropical list.** Two ***Tuberillo* sp.** records
  with origin "Tropics" fall through to **"Other"**.
- **D3. `biome()` maps any `"australia"` → `Tropical`.** Australia spans arid, temperate and
  tropical zones; the rule cannot distinguish a Tasmanian species from a Queensland one. (The one
  affected record, *Spherillo danae*, is eastern-Australian and plausibly subtropical — the rule is
  unsound even where its output happens to be defensible.)
- **D4. Two latent traps.** `region()`'s Europe list contains `"atlantic"`, so an "Atlantic coast of
  Brazil" locality would be filed as **Europe & Mediterranean**; and `" asia"` has a leading space,
  so a bare `"Asia"` would not match and would fall through to "Other". Neither fires on current
  data.

These are husbandry-derived and hobby-scoped, so the stakes are lower than A/B — but the fix is to
put a `biogeographic_realm` and `biome` field on the 112 records rather than inferring biogeography
by substring from a prose locality string. 112 rows is small enough to curate once and be right.

---

## Recommended order

1. **A3** — controlled vocabulary for `reproduction`; stop parsing prose. Two wrong species,
   published, and the cheapest fix here.
2. **A1 / A4 / A5** — resolve every family against a WoRMS AphiaID. That single change decides the
   Epicaridea question, empties the incertae sedis bucket, merges the 6 misspelling duplicates,
   fixes *Lakeamphisopus*, and gives you `extinct` for free.
3. **A2 / A6** — correct the 12 realms from WoRMS flags; emit suborder realm as a set.
4. **B1** — make `realm` a list so Ligiidae and Microparasellidae can be described truthfully.
5. **B2** — scope the terrestrial axes explicitly; add the family-level aquatic trophic guilds
   (~2,400 notes, high confidence, low effort).
6. **B3** — full WoRMS crossmatch (~290 requests); store `worms_aphia_id` and `worms_status`.
7. **C / D** — per-entry review and a `source` field on `ecology.json`.

Steps 2–3 are one script: fetch AphiaID → classification → environment flags per family, write
`data/isopoda_suborders.json` from the response instead of by hand, and keep the AphiaID in the file
so the next audit is a diff rather than a re-derivation.
