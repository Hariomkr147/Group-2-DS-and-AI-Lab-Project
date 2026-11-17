CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
CREATE SCHEMA IF NOT EXISTS ncert_research;
REVOKE ALL ON SCHEMA ncert_research FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS ncert_research.releases (
    release_id text PRIMARY KEY,
    source_manifest_sha256 text NOT NULL,
    content_sha256 text NOT NULL,
    embedding_model text NOT NULL,
    embedding_revision text NOT NULL,
    passage_count integer NOT NULL CHECK (passage_count >= 0),
    review_status text NOT NULL CHECK (review_status IN ('candidate', 'approved')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ncert_research.passages (
    release_id text NOT NULL REFERENCES ncert_research.releases(release_id),
    passage_id text NOT NULL,
    grade smallint NOT NULL CHECK (grade BETWEEN 6 AND 10),
    subject text NOT NULL CHECK (subject IN ('maths', 'science')),
    book_code text NOT NULL,
    chapter smallint NOT NULL CHECK (chapter > 0),
    physical_page integer NOT NULL CHECK (physical_page > 0),
    source_file text NOT NULL,
    source_sha256 text NOT NULL,
    source_url text NOT NULL,
    heading text NOT NULL,
    content text NOT NULL CHECK (length(trim(content)) > 0),
    review_flags text[] NOT NULL DEFAULT '{}',
    review_status text NOT NULL CHECK (review_status IN ('candidate', 'approved')),
    embedding extensions.vector(1024) NOT NULL,
    PRIMARY KEY (release_id, passage_id)
);

REVOKE ALL ON ALL TABLES IN SCHEMA ncert_research FROM PUBLIC, anon, authenticated;
