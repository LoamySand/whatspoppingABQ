-- Runs before 01_schema.sql (docker-entrypoint-initdb.d executes files in
-- filename order). Creates a separate database for Prefect's own
-- orchestration metadata (flow runs, automations, deployments, etc.) --
-- kept apart from the app's own `event_analytics`/`app` schema data so
-- Prefect's Alembic migrations never touch application tables and vice
-- versa. Fixes the recurring SQLite write-lock/corruption issue (see
-- SCRUM-55 notes) by giving Prefect a real concurrent-write-capable
-- backend instead of its SQLite default.
CREATE DATABASE prefect;

-- pg_trgm is required by Prefect's Postgres backend and is per-database,
-- so it has to be created inside `prefect` specifically, not the default
-- database this script started in.
\c prefect
CREATE EXTENSION IF NOT EXISTS pg_trgm;
