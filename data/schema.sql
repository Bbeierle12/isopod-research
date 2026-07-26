-- PostgreSQL schema implementing the taxonomic evaluation matrix as hard
-- constraints, corrected so it can actually hold THIS repository's data.
--
-- Fixes over the first-draft schema (see docs/reviews/2026-07-26-external-
-- review-reconciliation.md):
--   1. columns for open nomenclature + trade names — the draft's CHECKs
--      rejected "sp." with nowhere to put it, which would have dropped all 24
--      provisional forms on load;
--   2. a normalized reference_source table reached by FOREIGN KEY — the draft's
--      free-text source_citation was the exact anti-pattern criterion IV.2
--      fails the repo for;
--   3. accepted_taxon_id split from parent_taxon_id — a synonym's link to its
--      senior name is a different edge from its hierarchical parent;
--   4. UNIQUE ... NULLS NOT DISTINCT on the identity — otherwise every
--      unknown-authority row escapes the uniqueness/homonym guard.
--
-- Requires PostgreSQL 15+ (NULLS NOT DISTINCT). scripts/build_db.py loads an
-- equivalent SQLite build from the JSON + notes and reports compliance.

CREATE EXTENSION IF NOT EXISTS citext;

CREATE TYPE taxon_status_enum AS ENUM (
    'accepted', 'synonym', 'provisional', 'unresolved', 'needs_review',
    'deprecated', 'nomen_dubium', 'nomen_nudum'
);
CREATE TYPE record_kind_enum AS ENUM ('taxon', 'form', 'morph');

-- IV.2 Source Citation — normalized, one row per source, FK'd from every claim.
CREATE TABLE reference_source (
    reference_id SERIAL PRIMARY KEY,
    citation     TEXT NOT NULL,
    doi          TEXT,
    url          TEXT,
    kind         TEXT,                       -- 'monograph' | 'paper' | 'database' | ...
    CONSTRAINT uq_reference UNIQUE (citation)
);

-- Family-level authority + environment (WoRMS), kept separate from species so a
-- family AphiaID is never mistaken for a species id.
CREATE TABLE family (
    family_id      SERIAL PRIMARY KEY,
    name           VARCHAR(120) NOT NULL UNIQUE CHECK (name ~ '^[A-Z][a-z]+$'),
    suborder       VARCHAR(80)  NOT NULL,
    realm          VARCHAR(20)  NOT NULL,    -- primary realm
    realms         TEXT[]       NOT NULL,    -- full WoRMS environment set
    worms_aphia_id BIGINT,
    worms_status   VARCHAR(40),
    extinct        BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE taxonomy (
    taxon_id            SERIAL PRIMARY KEY,

    -- I. Nomenclatural compliance -------------------------------------------
    genus               VARCHAR(100) NOT NULL,
    species_epithet     VARCHAR(100),         -- NULL when identified only to genus
    subspecies_epithet  VARCHAR(100),
    open_nomenclature   VARCHAR(16),          -- 'sp.'/'cf.'/... — NEVER in the epithet
    trade_name          VARCHAR(120),         -- hobby label for undescribed forms

    authority_author    VARCHAR(180),
    authority_year      INTEGER,
    is_reassigned       BOOLEAN NOT NULL DEFAULT FALSE,  -- parenthesised authorship (ICZN 51.3)

    -- II. Taxonomic hierarchy & validity ------------------------------------
    record_kind         record_kind_enum  NOT NULL DEFAULT 'taxon',
    status              taxon_status_enum NOT NULL DEFAULT 'unresolved',
    suborder            VARCHAR(80),
    family              VARCHAR(120) REFERENCES family(name),
    parent_taxon_id     INTEGER REFERENCES taxonomy(taxon_id),   -- hierarchical parent
    accepted_taxon_id   INTEGER REFERENCES taxonomy(taxon_id),   -- senior synonym (II.1)
    extinct             BOOLEAN NOT NULL DEFAULT FALSE,

    -- IV. Provenance & authority --------------------------------------------
    gbif_id             BIGINT,
    worms_aphia_id      BIGINT,
    itis_tsn            BIGINT,
    placement_ref       INTEGER REFERENCES reference_source(reference_id),

    -- I.1 formatting
    CONSTRAINT chk_genus_capitalized CHECK (genus ~ '^[A-Z][a-z]+$'),
    CONSTRAINT chk_species_lowercase CHECK (
        species_epithet IS NULL OR species_epithet ~ '^[a-z][a-z-]+$'),
    CONSTRAINT chk_subspecies_lowercase CHECK (
        subspecies_epithet IS NULL OR subspecies_epithet ~ '^[a-z][a-z-]+$'),
    -- I.4 open nomenclature kept out of the epithet, and a record must carry
    -- either a real epithet or an open-nomenclature marker (never neither)
    CONSTRAINT chk_open_nomenclature CHECK (
        open_nomenclature IS NULL OR open_nomenclature IN ('sp.','spp.','cf.','aff.','var.','nr.')),
    CONSTRAINT chk_epithet_or_open CHECK (
        species_epithet IS NOT NULL OR open_nomenclature IS NOT NULL),

    -- I.2 year sanity
    CONSTRAINT chk_year CHECK (authority_year IS NULL OR authority_year BETWEEN 1700 AND 2100),

    -- III.2 whitespace
    CONSTRAINT chk_genus_ws   CHECK (genus = btrim(genus)),
    CONSTRAINT chk_species_ws CHECK (species_epithet IS NULL OR species_epithet = btrim(species_epithet)),

    -- II.1 a synonym must map to its accepted senior name
    CONSTRAINT chk_synonym_has_accepted CHECK (
        status <> 'synonym' OR accepted_taxon_id IS NOT NULL),

    -- II.3 / III.3 identity uniqueness — NULLS NOT DISTINCT so unknown-authority
    -- rows are still deduped; trade_name keeps distinct "Genus sp." forms apart.
    CONSTRAINT uq_identity UNIQUE NULLS NOT DISTINCT
        (genus, species_epithet, subspecies_epithet, open_nomenclature,
         trade_name, authority_author, authority_year)
);

CREATE INDEX ix_taxonomy_family ON taxonomy (family);
CREATE INDEX ix_taxonomy_status ON taxonomy (status);
CREATE INDEX ix_taxonomy_gbif   ON taxonomy (gbif_id);

-- A junior synonym may not also be marked accepted, and vice-versa.
ALTER TABLE taxonomy ADD CONSTRAINT chk_accepted_not_self
    CHECK (accepted_taxon_id IS NULL OR accepted_taxon_id <> taxon_id);
