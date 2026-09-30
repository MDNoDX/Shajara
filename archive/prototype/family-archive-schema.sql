-- =====================================================================
-- Family Archive — target relational schema (all phases)
-- Portable SQL (PostgreSQL primary; SQLite-compatible with minor edits).
-- Design rules:
--   * Facts are ASSERTIONS, never overwritten. Conflicts are two or more
--     active assertions about the same thing; resolution is a separate
--     record that keeps every assertion.
--   * Every assertion carries an evidence status and zero..n citations.
--   * Dates are stored as structured fuzzy dates, never forced exact.
--   * Names are a separate table; original forms are never overwritten.
--   * Nothing is deleted silently: soft-delete + audit log.
-- =====================================================================

-- ---------- Enumerations (as CHECK lists for portability) ------------
-- evidence_status: verified | probable | family_tradition | unverified | contradicted
-- privacy_level:   private | family | public
-- date_mode:       exact | month | year | about | before | after | between | unknown

-- ---------- Accounts & archives --------------------------------------
CREATE TABLE app_user (
  id            UUID PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  display_name  TEXT NOT NULL,
  ui_locale     TEXT NOT NULL DEFAULT 'en' CHECK (ui_locale IN ('en','uz','ru')),
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE archive (                       -- one family archive; demo is a separate archive
  id            UUID PRIMARY KEY,
  owner_id      UUID NOT NULL REFERENCES app_user(id),
  title         TEXT NOT NULL,
  is_demo       BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE archive_member (                -- FAMILY privacy level = these people
  archive_id    UUID REFERENCES archive(id) ON DELETE CASCADE,
  user_id       UUID REFERENCES app_user(id) ON DELETE CASCADE,
  role          TEXT NOT NULL CHECK (role IN ('owner','editor','contributor','viewer')),
  PRIMARY KEY (archive_id, user_id)
);

-- ---------- Structured fuzzy date (embedded columns pattern) ---------
-- Each dated row uses: <p>_mode, <p>_y, <p>_m, <p>_d, <p>_y2, <p>_m2, <p>_d2,
-- <p>_text (as written in the source), <p>_sort (derived, for ordering).

-- ---------- Places ---------------------------------------------------
CREATE TABLE place (
  id            UUID PRIMARY KEY,
  archive_id    UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,                -- as commonly used by the family
  historical_name TEXT,                       -- name at the time (e.g. pre-1991 forms)
  city          TEXT, region TEXT, country TEXT,
  latitude      NUMERIC(9,6), longitude NUMERIC(9,6),
  valid_from_y  INTEGER, valid_to_y INTEGER,  -- period the name/jurisdiction applied
  notes         TEXT,
  deleted_at    TIMESTAMP
);
CREATE INDEX ix_place_archive_name ON place(archive_id, name);

-- ---------- People & names -------------------------------------------
CREATE TABLE person (
  id            UUID PRIMARY KEY,
  archive_id    UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  sex           TEXT NOT NULL DEFAULT 'unknown' CHECK (sex IN ('female','male','unknown','other')),
  living        TEXT NOT NULL DEFAULT 'unknown' CHECK (living IN ('living','deceased','unknown')),
  privacy       TEXT NOT NULL DEFAULT 'private' CHECK (privacy IN ('private','family','public')),
  notes         TEXT,
  created_by    UUID REFERENCES app_user(id),
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at    TIMESTAMP
);
CREATE INDEX ix_person_archive ON person(archive_id) WHERE deleted_at IS NULL;

CREATE TABLE person_name (
  id            UUID PRIMARY KEY,
  person_id     UUID NOT NULL REFERENCES person(id) ON DELETE CASCADE,
  name_type     TEXT NOT NULL CHECK (name_type IN
                 ('birth','married','former','nickname','alternative','historical',
                  'local_language','arabic_script','cyrillic','religious','other')),
  given         TEXT, patronymic TEXT, surname TEXT,
  full_as_written TEXT,                       -- exact original form, never normalized
  script        TEXT,                         -- ISO 15924: Latn, Cyrl, Arab
  lang          TEXT,                         -- BCP-47: uz, ru, fa, ar, tg
  is_primary    BOOLEAN NOT NULL DEFAULT FALSE,
  search_key    TEXT NOT NULL,                -- lowercased, diacritics folded, for search only
  status        TEXT NOT NULL DEFAULT 'unverified'
);
CREATE INDEX ix_name_search ON person_name(search_key);
CREATE UNIQUE INDEX ux_name_primary ON person_name(person_id) WHERE is_primary;

-- ---------- Relationships --------------------------------------------
CREATE TABLE parent_child (
  id            UUID PRIMARY KEY,
  archive_id    UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  parent_id     UUID NOT NULL REFERENCES person(id),
  child_id      UUID NOT NULL REFERENCES person(id),
  nature        TEXT NOT NULL CHECK (nature IN
                 ('biological','adoptive','step','guardian','foster','unknown')),
  status        TEXT NOT NULL DEFAULT 'unverified',
  notes         TEXT,
  deleted_at    TIMESTAMP,
  CHECK (parent_id <> child_id)
);
CREATE UNIQUE INDEX ux_pc ON parent_child(parent_id, child_id, nature) WHERE deleted_at IS NULL;
CREATE INDEX ix_pc_child ON parent_child(child_id);

CREATE TABLE union_rel (                      -- marriage / partnership
  id            UUID PRIMARY KEY,
  archive_id    UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  person_a_id   UUID NOT NULL REFERENCES person(id),
  person_b_id   UUID NOT NULL REFERENCES person(id),
  union_type    TEXT NOT NULL CHECK (union_type IN ('marriage','religious_marriage','civil_partnership','partnership','unknown')),
  start_mode TEXT, start_y INT, start_m INT, start_d INT, start_y2 INT, start_m2 INT, start_d2 INT, start_text TEXT, start_sort INT,
  start_place_id UUID REFERENCES place(id),
  end_reason    TEXT CHECK (end_reason IN ('divorce','annulment','death','separation','unknown')),
  end_mode TEXT, end_y INT, end_m INT, end_d INT, end_y2 INT, end_m2 INT, end_d2 INT, end_text TEXT, end_sort INT,
  status        TEXT NOT NULL DEFAULT 'unverified',
  deleted_at    TIMESTAMP,
  CHECK (person_a_id <> person_b_id)
);
CREATE INDEX ix_union_a ON union_rel(person_a_id);
CREATE INDEX ix_union_b ON union_rel(person_b_id);

CREATE TABLE sibling_rel (                    -- only when shared parents are NOT recorded
  id            UUID PRIMARY KEY,
  person_a_id   UUID NOT NULL REFERENCES person(id),
  person_b_id   UUID NOT NULL REFERENCES person(id),
  nature        TEXT NOT NULL CHECK (nature IN ('full','half','step','adoptive','unknown')),
  status        TEXT NOT NULL DEFAULT 'unverified'
);

-- ---------- Events (first-class) -------------------------------------
CREATE TABLE event (
  id            UUID PRIMARY KEY,
  archive_id    UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  event_type    TEXT NOT NULL CHECK (event_type IN
                 ('birth','death','burial','marriage','divorce','education','employment',
                  'military','migration','residence','religious','achievement','travel',
                  'family_event','historical_event','other')),
  is_historical_context BOOLEAN NOT NULL DEFAULT FALSE,   -- general history, user-approved only
  title         TEXT,
  description   TEXT,
  d_mode TEXT, d_y INT, d_m INT, d_d INT, d_y2 INT, d_m2 INT, d_d2 INT, d_text TEXT, d_sort INT,
  place_id      UUID REFERENCES place(id),
  to_place_id   UUID REFERENCES place(id),            -- migration destination
  status        TEXT NOT NULL DEFAULT 'unverified',
  origin        TEXT NOT NULL DEFAULT 'user' CHECK (origin IN ('user','ai_suggested_approved','import')),
  privacy       TEXT NOT NULL DEFAULT 'family',
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at    TIMESTAMP
);
CREATE INDEX ix_event_sort ON event(archive_id, d_sort);
CREATE INDEX ix_event_type ON event(archive_id, event_type);

CREATE TABLE event_participant (
  event_id      UUID REFERENCES event(id) ON DELETE CASCADE,
  person_id     UUID REFERENCES person(id) ON DELETE CASCADE,
  role          TEXT NOT NULL DEFAULT 'principal',    -- principal, spouse, witness, informant...
  PRIMARY KEY (event_id, person_id, role)
);
CREATE INDEX ix_ep_person ON event_participant(person_id);

-- ---------- Conflicts & resolutions ----------------------------------
-- A conflict is DERIVED (>=2 incompatible active assertions of the same
-- kind for the same subject). Resolution never deletes an assertion.
CREATE TABLE conflict_resolution (
  id            UUID PRIMARY KEY,
  subject_type  TEXT NOT NULL,                -- 'person'
  subject_id    UUID NOT NULL,
  claim_kind    TEXT NOT NULL,                -- 'birth', 'death', 'parent'...
  state         TEXT NOT NULL CHECK (state IN ('unresolved','preferred_selected','resolved')),
  preferred_event_id UUID REFERENCES event(id),
  rationale     TEXT,                         -- required when state <> 'unresolved'
  decided_by    UUID REFERENCES app_user(id),
  decided_at    TIMESTAMP,
  UNIQUE (subject_type, subject_id, claim_kind)
);

-- ---------- Sources & citations --------------------------------------
CREATE TABLE source (
  id            UUID PRIMARY KEY,
  archive_id    UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  title         TEXT NOT NULL,
  source_type   TEXT NOT NULL CHECK (source_type IN
                 ('official_document','certificate','book','archive_record','website','interview',
                  'family_member','photograph','letter','newspaper','other')),
  author        TEXT, repository TEXT, url TEXT, reference TEXT,
  d_mode TEXT, d_y INT, d_m INT, d_d INT, d_text TEXT,
  description   TEXT,
  reliability   TEXT,                          -- free-text reliability notes
  original_or_derivative TEXT CHECK (original_or_derivative IN ('original','derivative','authored','unknown')),
  deleted_at    TIMESTAMP
);

CREATE TABLE citation (                        -- links ONE source to ONE assertion
  id            UUID PRIMARY KEY,
  source_id     UUID NOT NULL REFERENCES source(id),
  target_type   TEXT NOT NULL CHECK (target_type IN
                 ('event','parent_child','union_rel','sibling_rel','person_name','story','photo_person')),
  target_id     UUID NOT NULL,
  detail        TEXT,                          -- page, entry no., minute in recording
  quote_original TEXT,                         -- transcription in original language
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_cit_target ON citation(target_type, target_id);
CREATE INDEX ix_cit_source ON citation(source_id);

-- ---------- Stories, media, documents --------------------------------
CREATE TABLE story (
  id UUID PRIMARY KEY, archive_id UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  title TEXT NOT NULL, body TEXT NOT NULL, lang TEXT,
  d_mode TEXT, d_y INT, d_y2 INT, d_text TEXT, d_sort INT,
  place_id UUID REFERENCES place(id),
  told_by_person_id UUID REFERENCES person(id), told_by_text TEXT,
  recorded_on DATE, status TEXT NOT NULL DEFAULT 'family_tradition',
  ai_assisted BOOLEAN NOT NULL DEFAULT FALSE,   -- prose shaped by AI is always flagged
  privacy TEXT NOT NULL DEFAULT 'family', deleted_at TIMESTAMP
);
CREATE TABLE story_person (story_id UUID REFERENCES story(id) ON DELETE CASCADE,
  person_id UUID REFERENCES person(id) ON DELETE CASCADE, PRIMARY KEY (story_id, person_id));

CREATE TABLE life_story_chapter (
  id UUID PRIMARY KEY, person_id UUID NOT NULL REFERENCES person(id) ON DELETE CASCADE,
  heading TEXT NOT NULL, position INT NOT NULL, body TEXT, ai_assisted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE media_file (                      -- content-addressed blob store
  id UUID PRIMARY KEY, archive_id UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  sha256 TEXT NOT NULL, mime TEXT NOT NULL, bytes BIGINT NOT NULL,
  width INT, height INT, original_filename TEXT, storage_key TEXT NOT NULL,
  UNIQUE (archive_id, sha256)
);

CREATE TABLE photo (
  id UUID PRIMARY KEY, archive_id UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  media_id UUID NOT NULL REFERENCES media_file(id),
  title TEXT, description TEXT, alt_text TEXT, photographer TEXT,
  d_mode TEXT, d_y INT, d_m INT, d_d INT, d_y2 INT, d_text TEXT, d_sort INT,
  place_id UUID REFERENCES place(id), source_id UUID REFERENCES source(id),
  privacy TEXT NOT NULL DEFAULT 'family', deleted_at TIMESTAMP
);
CREATE TABLE photo_person (                    -- a region in a photo; person may stay unknown
  id UUID PRIMARY KEY, photo_id UUID NOT NULL REFERENCES photo(id) ON DELETE CASCADE,
  person_id UUID REFERENCES person(id),        -- NULL = unidentified, never guessed
  region_x REAL, region_y REAL, region_w REAL, region_h REAL,   -- 0..1 relative box
  label_text TEXT, status TEXT NOT NULL DEFAULT 'unverified',
  confirmed_by UUID REFERENCES app_user(id)
);

CREATE TABLE document (
  id UUID PRIMARY KEY, archive_id UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  media_id UUID REFERENCES media_file(id),
  title TEXT NOT NULL, doc_type TEXT NOT NULL,
  d_mode TEXT, d_y INT, d_m INT, d_d INT, d_text TEXT, d_sort INT,
  place_id UUID REFERENCES place(id), description TEXT, transcription TEXT, notes TEXT,
  source_id UUID REFERENCES source(id),        -- a document is usually also a source
  privacy TEXT NOT NULL DEFAULT 'private', deleted_at TIMESTAMP
);
CREATE TABLE document_person (document_id UUID REFERENCES document(id) ON DELETE CASCADE,
  person_id UUID REFERENCES person(id) ON DELETE CASCADE, role TEXT,
  PRIMARY KEY (document_id, person_id));
CREATE TABLE document_event (document_id UUID REFERENCES document(id) ON DELETE CASCADE,
  event_id UUID REFERENCES event(id) ON DELETE CASCADE, PRIMARY KEY (document_id, event_id));
CREATE TABLE event_media (event_id UUID REFERENCES event(id) ON DELETE CASCADE,
  photo_id UUID REFERENCES photo(id) ON DELETE CASCADE, PRIMARY KEY (event_id, photo_id));

-- ---------- Research -------------------------------------------------
CREATE TABLE research_question (
  id UUID PRIMARY KEY, archive_id UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('not_started','in_progress','partially_solved','solved','unresolved')),
  conclusion TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE research_item (                   -- notes, hypotheses, evidence, all in order
  id UUID PRIMARY KEY, question_id UUID NOT NULL REFERENCES research_question(id) ON DELETE CASCADE,
  item_type TEXT NOT NULL CHECK (item_type IN ('note','hypothesis','evidence','conflict','task')),
  body TEXT NOT NULL, source_id UUID REFERENCES source(id), position INT NOT NULL
);
CREATE TABLE research_subject (question_id UUID REFERENCES research_question(id) ON DELETE CASCADE,
  subject_type TEXT NOT NULL, subject_id UUID NOT NULL, PRIMARY KEY (question_id, subject_type, subject_id));

CREATE TABLE interview (                        -- original always preserved
  id UUID PRIMARY KEY, archive_id UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  interviewee_person_id UUID REFERENCES person(id), interviewer TEXT, held_on DATE,
  lang TEXT, audio_media_id UUID REFERENCES media_file(id), transcript TEXT,
  source_id UUID REFERENCES source(id)          -- becomes a citable source
);

-- ---------- Branches, tags, timeline, books --------------------------
CREATE TABLE family_branch (
  id UUID PRIMARY KEY, archive_id UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  name TEXT NOT NULL, surname TEXT, founder_person_id UUID REFERENCES person(id), description TEXT
);
CREATE TABLE tag (id UUID PRIMARY KEY, archive_id UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  label TEXT NOT NULL, UNIQUE (archive_id, label));
CREATE TABLE tag_link (tag_id UUID REFERENCES tag(id) ON DELETE CASCADE,
  target_type TEXT NOT NULL, target_id UUID NOT NULL, PRIMARY KEY (tag_id, target_type, target_id));

-- TimelineEntry is a VIEW, not a table: events + unions + dated stories/photos,
-- so there is no duplicated date data to drift out of sync.

CREATE TABLE book_project (
  id UUID PRIMARY KEY, archive_id UUID NOT NULL REFERENCES archive(id) ON DELETE CASCADE,
  title TEXT NOT NULL, subtitle TEXT, author_line TEXT, dedication TEXT, preface TEXT,
  closing TEXT, theme TEXT NOT NULL DEFAULT 'classic' CHECK (theme IN ('classic','modern','heritage','photo_album')),
  page_size TEXT NOT NULL DEFAULT 'A4', scope_type TEXT NOT NULL, scope_id UUID,
  include_living_details BOOLEAN NOT NULL DEFAULT FALSE,
  edition_label TEXT, cover_photo_id UUID REFERENCES photo(id)
);
CREATE TABLE book_section (
  id UUID PRIMARY KEY, book_id UUID NOT NULL REFERENCES book_project(id) ON DELETE CASCADE,
  section_type TEXT NOT NULL, position INT NOT NULL, included BOOLEAN NOT NULL DEFAULT TRUE,
  config_json TEXT                              -- per-section options (generation no., selections)
);

-- ---------- Privacy overrides & audit --------------------------------
CREATE TABLE privacy_setting (
  target_type TEXT NOT NULL, target_id UUID NOT NULL,
  level TEXT NOT NULL CHECK (level IN ('private','family','public')),
  PRIMARY KEY (target_type, target_id)
);
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY, archive_id UUID NOT NULL, user_id UUID,
  action TEXT NOT NULL, target_type TEXT NOT NULL, target_id UUID NOT NULL,
  before_json TEXT, after_json TEXT, at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_audit_target ON audit_log(target_type, target_id);
