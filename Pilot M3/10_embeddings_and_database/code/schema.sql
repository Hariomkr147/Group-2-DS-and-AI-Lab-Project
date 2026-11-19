CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS ncert_content;
CREATE SCHEMA IF NOT EXISTS ncert_private;
REVOKE ALL ON SCHEMA ncert_private FROM PUBLIC;
CREATE TABLE IF NOT EXISTS ncert_content.releases (
    corpus_version text PRIMARY KEY, fingerprint text NOT NULL, manifest jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS ncert_content.sources (
    corpus_version text REFERENCES ncert_content.releases, source_id text, metadata jsonb NOT NULL,
    PRIMARY KEY(corpus_version, source_id)
);
CREATE TABLE IF NOT EXISTS ncert_content.concepts (
    corpus_version text REFERENCES ncert_content.releases, concept_id text, payload jsonb NOT NULL,
    PRIMARY KEY(corpus_version, concept_id)
);
CREATE TABLE IF NOT EXISTS ncert_content.chunks (
    corpus_version text REFERENCES ncert_content.releases, chunk_id text, source_id text NOT NULL,
    text text NOT NULL, page_start integer CHECK(page_start > 0), page_end integer CHECK(page_end >= page_start),
    payload jsonb NOT NULL, embedding vector(384) NOT NULL,
    PRIMARY KEY(corpus_version, chunk_id),
    FOREIGN KEY(corpus_version, source_id) REFERENCES ncert_content.sources
);
CREATE TABLE IF NOT EXISTS ncert_content.chunk_concepts (
    corpus_version text, chunk_id text, concept_id text,
    PRIMARY KEY(corpus_version, chunk_id, concept_id),
    FOREIGN KEY(corpus_version, chunk_id) REFERENCES ncert_content.chunks,
    FOREIGN KEY(corpus_version, concept_id) REFERENCES ncert_content.concepts
);
CREATE TABLE IF NOT EXISTS ncert_content.questions (
    corpus_version text REFERENCES ncert_content.releases, question_id text, payload jsonb NOT NULL,
    PRIMARY KEY(corpus_version, question_id)
);
CREATE TABLE IF NOT EXISTS ncert_private.answers (
    corpus_version text, question_id text, payload jsonb NOT NULL,
    PRIMARY KEY(corpus_version, question_id),
    FOREIGN KEY(corpus_version, question_id) REFERENCES ncert_content.questions
);
REVOKE ALL ON ncert_private.answers FROM PUBLIC;
CREATE TABLE IF NOT EXISTS ncert_content.prerequisite_edges (
    corpus_version text, prerequisite_id text, dependent_id text, payload jsonb NOT NULL,
    CHECK(prerequisite_id <> dependent_id),
    PRIMARY KEY(corpus_version, prerequisite_id, dependent_id),
    FOREIGN KEY(corpus_version, prerequisite_id) REFERENCES ncert_content.concepts,
    FOREIGN KEY(corpus_version, dependent_id) REFERENCES ncert_content.concepts
);
CREATE OR REPLACE VIEW ncert_content.learner_questions AS
    SELECT corpus_version, question_id, payload FROM ncert_content.questions;
