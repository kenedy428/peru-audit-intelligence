-- Runs only on first initialization of the project's PostgreSQL 18 volume.
-- The official entrypoint connects to POSTGRES_DB (audit_intelligence).
CREATE EXTENSION IF NOT EXISTS vector;
