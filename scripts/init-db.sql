-- =============================================================================
-- Defense PM Tool - Database Initialization Script
-- =============================================================================
-- This script is automatically executed when PostgreSQL container starts.
-- It creates required extensions and sets up initial database configuration.
--
-- Usage:
--   Mounted to /docker-entrypoint-initdb.d/init.sql in PostgreSQL container
-- =============================================================================

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "ltree";

-- Create performance-related configuration (optional)
-- These can be overridden by postgresql.conf or environment variables

-- Log slow queries (> 1 second) for performance monitoring
ALTER SYSTEM SET log_min_duration_statement = '1000';

-- Enable query statistics collection
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';

-- Grant privileges to application user (if using different user than owner)
-- GRANT ALL PRIVILEGES ON DATABASE defense_pm_prod TO defense_pm;

-- Create application schema (if needed)
-- CREATE SCHEMA IF NOT EXISTS app;

SELECT 'Database initialization complete' AS status;
