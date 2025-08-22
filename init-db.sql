-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a simple test to verify pgvector is working
CREATE TABLE IF NOT EXISTS test_vectors (
    id SERIAL PRIMARY KEY,
    embedding vector(1536)  -- OpenAI embedding dimension
);

-- Test insert
INSERT INTO test_vectors (embedding) VALUES ('[0.1, 0.2, 0.3]'::vector);