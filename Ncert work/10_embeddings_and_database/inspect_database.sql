-- Run in pgAdmin Query Tool while connected to ncert_pilot. Read-only transaction.
BEGIN READ ONLY;
SELECT current_database(), inet_server_addr(), inet_server_port();
SELECT corpus_version, count(*) AS chunks FROM ncert_content.chunks GROUP BY corpus_version;
SELECT 'current_release_retrieval_chunks' AS kind, count(*) FROM ncert_content.chunks
WHERE corpus_version='ncert-pilot-fd981363bc7f493a'
UNION ALL SELECT 'source_questions', count(*) FROM ncert_content.ncert_questions
UNION ALL SELECT 'worked_examples', count(*) FROM ncert_content.ncert_worked_examples
UNION ALL SELECT 'official_private_answers', count(*) FROM ncert_private.ncert_answers
UNION ALL SELECT 'eedi_misconceptions', count(*) FROM ncert_diag.misconceptions
UNION ALL SELECT 'eedi_constructs', count(*) FROM ncert_diag.constructs;

SELECT corpus_version, chunk_id, source_id, page_start, page_end, text,
       vector_dims(embedding) AS embedding_dimensions
FROM ncert_content.chunks WHERE corpus_version='ncert-pilot-fd981363bc7f493a'
ORDER BY chunk_id LIMIT 30;

SELECT question_id, source_id, answer_available, payload->>'prompt' AS question,
       payload->>'review_status' AS review_status
FROM ncert_content.ncert_questions ORDER BY source_id, question_id LIMIT 30;

-- Owner-only answer-key review; never copy this result into a learner endpoint.
SELECT q.question_id, q.payload->>'prompt' AS question,
       a.payload->>'answer' AS official_answer,
       a.payload->>'page_start' AS answer_physical_page
FROM ncert_content.ncert_questions q
LEFT JOIN ncert_private.ncert_answers a USING (question_id)
ORDER BY q.source_id, q.question_id LIMIT 30;

SELECT misconception_id, text, construct_ids, licence, vector_dims(embedding)
FROM ncert_diag.misconceptions ORDER BY misconception_id LIMIT 20;
COMMIT;
