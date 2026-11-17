# RAG

Retrieval for the tutor: embed NCERT chunks, store them in PostgreSQL with pgvector, and fetch the best chunks for a question.

- Source pipeline: `Ncert work/10_embeddings_and_database` (embedding, loading) and `Ncert work/11_retrieval_and_evaluation`.
- Serving: the backend calls this code from `backend/app/services`.
- Vector store: Supabase or local PostgreSQL with the `vector` extension.
