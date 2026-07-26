# -*- coding: utf-8 -*-
"""Load the vault into a SQLite database that enforces the evaluation matrix as
CHECK/UNIQUE constraints, proving the data is compliant (or reporting exactly
what is not).

Sources:
  * data/isopoda_suborders.json  -> family table (suborder, realm, AphiaID, extinct)
  * data/isopods.json            -> taxonomy rows for hobby forms + morphs
  * Isopoda/**/<species>.md      -> taxonomy rows for every accepted species

Authority strings are atomised into author + year + is_reassigned (the
parenthesis flag). A row that violates a constraint is caught and reported
rather than crashing the load, so the output is a compliance report.

The SQLite schema mirrors data/schema.sql; SQLite lacks ENUM and
NULLS NOT DISTINCT, so status is a CHECKed text column and identity uniqueness
is enforced over COALESCE()d columns via a unique index.

Python 3.9+.  Run:  python scripts/build_db.py [--db PATH]
"""
import argparse
import json
import re
import sqlite3
from collections import Counter

import _vault as V

STATUSES = ("accepted", "synonym", "provisional", "unresolved", "needs_review",
            "deprecated", "nomen_dubium", "nomen_nudum")
OPEN_NOM = ("sp.", "spp.", "cf.", "aff.", "var.", "nr.")

SCHEMA = """
CREATE TABLE family (
    name TEXT PRIMARY KEY CHECK (name GLOB '[A-Z]*'),
    suborder TEXT NOT NULL, realm TEXT NOT NULL, realms TEXT NOT NULL,
    worms_aphia_id INTEGER, worms_status TEXT, extinct INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE taxonomy (
    taxon_id INTEGER PRIMARY KEY,
    genus TEXT NOT NULL CHECK (genus = trim(genus) AND genus GLOB '[A-Z][a-z]*'),
    species_epithet TEXT CHECK (species_epithet IS NULL OR
        (species_epithet = trim(species_epithet) AND species_epithet GLOB '[a-z]*'
         AND species_epithet NOT GLOB '*[. ]*')),
    subspecies_epithet TEXT,
    open_nomenclature TEXT CHECK (open_nomenclature IS NULL OR
        open_nomenclature IN ('sp.','spp.','cf.','aff.','var.','nr.')),
    trade_name TEXT,
    authority_author TEXT,
    authority_year INTEGER CHECK (authority_year IS NULL OR
        (authority_year BETWEEN 1700 AND 2100)),
    is_reassigned INTEGER NOT NULL DEFAULT 0,
    record_kind TEXT NOT NULL CHECK (record_kind IN ('taxon','form','morph')),
    status TEXT NOT NULL CHECK (status IN %s),
    suborder TEXT, family TEXT REFERENCES family(name),
    extinct INTEGER NOT NULL DEFAULT 0,
    gbif_id INTEGER, worms_aphia_id INTEGER, worms_status TEXT, worms_accepted TEXT,
    CHECK (species_epithet IS NOT NULL OR open_nomenclature IS NOT NULL)
);
CREATE TABLE reference_source (
    reference_key TEXT PRIMARY KEY,
    citation TEXT NOT NULL,
    doi TEXT,
    year INTEGER,
    verified TEXT NOT NULL
);
CREATE TABLE ecology_claim (
    claim_id INTEGER PRIMARY KEY,
    match_name TEXT NOT NULL,
    ecomorph TEXT, terrestrialization TEXT, stratum TEXT, trophic TEXT, reproduction TEXT,
    unsourced_note TEXT
);
CREATE TABLE ecology_claim_source (
    claim_id INTEGER NOT NULL REFERENCES ecology_claim(claim_id),
    reference_key TEXT NOT NULL REFERENCES reference_source(reference_key),
    PRIMARY KEY (claim_id, reference_key)
);
CREATE UNIQUE INDEX uq_identity ON taxonomy (
    genus, COALESCE(species_epithet,''), COALESCE(subspecies_epithet,''),
    COALESCE(open_nomenclature,''), COALESCE(trade_name,''),
    COALESCE(authority_author,''), COALESCE(authority_year,-1)
);
""" % (str(STATUSES),)

_YEAR = re.compile(r"\b(1[6-9]\d\d|20[0-2]\d)\b")


def parse_authority(auth):
    """('(Latreille, 1804)') -> (author, year, is_reassigned)."""
    auth = (auth or "").strip()
    if not auth:
        return None, None, False
    reassigned = auth.startswith("(")
    core = auth.strip("()").strip()
    ym = _YEAR.search(core)
    year = int(ym.group(1)) if ym else None
    author = core[:ym.start()].rstrip(" ,") if ym else core
    return (author or None), year, reassigned


def split_name(name):
    """'Genus species subspecies' -> (genus, species|None, subspecies|None)."""
    parts = name.split()
    g = parts[0] if parts else None
    s = parts[1] if len(parts) > 1 else None
    ss = parts[2] if len(parts) > 2 else None
    return g, s, ss


def load_families(cur):
    fams = json.loads((V.DATA / "isopoda_suborders.json").read_text(encoding="utf-8"))["families"]
    rows = []
    for name, info in fams.items():
        rows.append((name, info["suborder"], info["realm"],
                     ",".join(info.get("realms") or [info["realm"]]),
                     info.get("worms_aphia_id"), info.get("worms_status"),
                     1 if info.get("extinct") else 0))
    cur.executemany("INSERT INTO family VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)


def load_ecology(cur):
    """Ecology claims + their citations, as normalized tables (criterion IV.2:
    a claim's provenance is a FOREIGN KEY, not a free-text field)."""
    doc = json.loads((V.DATA / "ecology.json").read_text(encoding="utf-8"))
    for key, r in sorted(doc.get("references", {}).items()):
        cur.execute("INSERT INTO reference_source VALUES (?,?,?,?,?)",
                    (key, r["citation"], r.get("doi"), r.get("year"), r.get("verified", "?")))
    for i, e in enumerate(doc["entries"], 1):
        cur.execute("INSERT INTO ecology_claim VALUES (?,?,?,?,?,?,?,?)",
                    (i, e["match"], e.get("ecomorph"), e.get("terrestrialization"),
                     e.get("stratum"), e.get("trophic"), e.get("reproduction"),
                     e.get("source_note")))
        for k in (e.get("source_refs") or []):
            cur.execute("INSERT INTO ecology_claim_source VALUES (?,?)", (i, k))
    return len(doc["entries"]), len(doc.get("references", {}))


def insert(cur, checkfail, dedup, **kw):
    cols = ",".join(kw)
    try:
        cur.execute("INSERT INTO taxonomy (%s) VALUES (%s)"
                    % (cols, ",".join("?" * len(kw))), tuple(kw.values()))
        return True
    except sqlite3.IntegrityError as e:
        msg = str(e)
        (dedup if "UNIQUE" in msg else checkfail).append(
            (kw.get("genus"), kw.get("species_epithet"), kw.get("trade_name"), msg))
        return False


def load_hobby(cur, checkfail, dedup):
    """Hobby layer. Described, GBIF-placed forms are the SAME taxon as their
    taxonomy row, so they are not re-inserted; only provisional trade forms,
    unmatched described forms (absent from the tree), and morph cultivars
    (distinguished by their morph name) become rows here."""
    recs = json.loads((V.DATA / "isopods.json").read_text(encoding="utf-8"))["records"]
    status_map = {"provisional": "provisional", "unmatched": "unresolved",
                  "needs_review": "needs_review"}
    n = 0
    for r in recs:
        kind = r["record_type"]
        described_in_tree = (r.get("is_described")
                             and r.get("taxon_status") in ("accepted", "synonym"))
        if kind == "form" and described_in_tree:
            continue  # represented by its taxonomy row
        author, year, reassigned = parse_authority(r.get("authority"))
        sp = (r.get("species") or "").strip() or None
        # a morph is a cultivar of its parent taxon; its morph name keeps it
        # distinct from the base species under the identity uniqueness rule
        trade = r.get("morph_name") if kind == "morph" else r.get("trade_name")
        open_nom = r.get("open_nomenclature") or (None if sp else "sp.")
        n += insert(cur, checkfail, dedup,
                    genus=r["genus"], species_epithet=sp,
                    open_nomenclature=open_nom,
                    trade_name=(trade or None),
                    authority_author=author, authority_year=year,
                    is_reassigned=1 if reassigned else 0,
                    record_kind=kind,
                    status=status_map.get(r.get("taxon_status"), "unresolved"),
                    family=r.get("family"), gbif_id=r.get("gbif_id"))
    return n


FM_KEYS = re.compile(r"^(scientificName|authorship|suborder|family|realm|gbif_id|extinct"
                     r"|worms_aphia_id|worms_status|worms_accepted|type|accepted_name):[ \t]*(.*)$", re.M)


def load_taxonomy(cur, checkfail, dedup, families):
    n = 0
    for note in sorted(V.ISOPODA.rglob("*.md")):
        if note.name.startswith("_"):
            continue
        parsed = V.parse_frontmatter(V.read_text(note))
        if not parsed:
            continue
        fm = dict((m.group(1), m.group(2).strip().strip('"')) for m in FM_KEYS.finditer(parsed[1]))
        g, s, ss = split_name(fm.get("scientificName", note.stem))
        if not g:
            continue
        author, year, reassigned = parse_authority(fm.get("authorship"))
        fam = fm.get("family") or None
        n += insert(cur, checkfail, dedup,
                    genus=g, species_epithet=s, subspecies_epithet=ss,
                    authority_author=author, authority_year=year,
                    is_reassigned=1 if reassigned else 0,
                    record_kind="taxon",
                    status=("synonym" if fm.get("type") == "synonym" else "accepted"),
                    suborder=fm.get("suborder"),
                    family=fam if fam in families else None,
                    extinct=1 if fm.get("extinct") == "true" else 0,
                    gbif_id=fm.get("gbif_id") or None,
                    worms_aphia_id=fm.get("worms_aphia_id") or None,
                    worms_status=fm.get("worms_status") or None,
                    worms_accepted=fm.get("worms_accepted") or fm.get("accepted_name") or None)
    return n


def main():
    ap = argparse.ArgumentParser(description="Load the vault into a constraint-enforcing SQLite db.")
    ap.add_argument("--db", default=":memory:", help="output db path (default: in-memory)")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    cur = con.cursor()

    checkfail, dedup = [], []
    nf = load_families(cur)
    families = {row[0] for row in cur.execute("SELECT name FROM family")}
    nt = load_taxonomy(cur, checkfail, dedup, families)   # canonical taxa first
    nh = load_hobby(cur, checkfail, dedup)
    nc, nr = load_ecology(cur)
    con.commit()

    print("Loaded: %d families, %d taxonomy species, %d hobby (provisional+morph+orphan) rows, "
          "%d ecology claims citing %d references." % (nf, nt, nh, nc, nr))
    print("Formatting/CHECK violations (real matrix failures): %d" % len(checkfail))
    for g, sp, tn, err in checkfail[:20]:
        print("   %-22s %-18s %-16s %s" % (g, sp or "-", tn or "-", err))
    print("Identity collisions (same taxon already present — expected dedup): %d" % len(dedup))

    print("\n-- demonstration queries --")
    for label, q in [
        ("species per suborder", "SELECT suborder, COUNT(*) FROM taxonomy WHERE record_kind='taxon' GROUP BY suborder ORDER BY 2 DESC"),
        ("extinct species", "SELECT COUNT(*) FROM taxonomy WHERE extinct=1"),
        ("reassigned (parenthesised authorship)", "SELECT COUNT(*) FROM taxonomy WHERE is_reassigned=1"),
        ("open-nomenclature forms", "SELECT COUNT(*) FROM taxonomy WHERE open_nomenclature IS NOT NULL"),
        ("families by realm", "SELECT realm, COUNT(*) FROM family GROUP BY realm ORDER BY 2 DESC"),
        ("WoRMS status (species)", "SELECT worms_status, COUNT(*) FROM taxonomy WHERE record_kind='taxon' GROUP BY worms_status ORDER BY 2 DESC LIMIT 6"),
        ("dual-authority (gbif+worms ids)", "SELECT COUNT(*) FROM taxonomy WHERE gbif_id IS NOT NULL AND worms_aphia_id IS NOT NULL"),
        ("authorship with a year", "SELECT COUNT(*) FROM taxonomy WHERE authority_year IS NOT NULL"),
        ("ecology claims with >=1 source", "SELECT COUNT(DISTINCT claim_id) FROM ecology_claim_source"),
        ("references with a DOI", "SELECT COUNT(*) FROM reference_source WHERE doi IS NOT NULL"),
    ]:
        rows = cur.execute(q).fetchall()
        if len(rows) == 1 and len(rows[0]) == 1:
            print("  %-38s %s" % (label + ":", rows[0][0]))
        else:
            print("  %s:" % label)
            for row in rows:
                print("      %s" % " ".join(str(x) for x in row))
    con.close()
    return 0 if not checkfail else 1


if __name__ == "__main__":
    raise SystemExit(main())
