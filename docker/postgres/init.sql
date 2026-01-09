-- =============================================================================
-- Defense PM Tool - PostgreSQL Initialization Script
-- =============================================================================
-- This script runs automatically on first database initialization.
-- It creates required extensions and sets up the test database.
--
-- Note: This script only runs when the postgres_data volume is empty.
-- To re-run, use: docker-compose down -v && docker-compose up -d postgres
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Enable Required Extensions for Development Database
-- -----------------------------------------------------------------------------

-- UUID generation for primary keys
-- Usage: id UUID DEFAULT uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Hierarchical data type for WBS (Work Breakdown Structure)
-- Usage: path LTREE for efficient ancestor/descendant queries
-- Example queries:
--   WHERE path <@ '1.2'        (all descendants of 1.2)
--   WHERE '1.2.3.4' <@ path    (all ancestors of 1.2.3.4)
--   WHERE path ~ '1.2.*{1}'    (direct children of 1.2)
CREATE EXTENSION IF NOT EXISTS ltree;

-- Additional useful extensions (optional, uncomment if needed)
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- Trigram similarity for fuzzy search
-- CREATE EXTENSION IF NOT EXISTS btree_gist;   -- GiST index for range types

-- -----------------------------------------------------------------------------
-- Create Test Database
-- -----------------------------------------------------------------------------
-- Separate database for running integration tests without affecting dev data.
-- Tests can safely truncate tables and reset data.
-- -----------------------------------------------------------------------------

-- Create the test database
CREATE DATABASE defense_pm_test;

-- Grant full privileges to the dev user
GRANT ALL PRIVILEGES ON DATABASE defense_pm_test TO dev_user;

-- -----------------------------------------------------------------------------
-- Initialize Test Database Extensions
-- -----------------------------------------------------------------------------
-- Connect to the test database and enable the same extensions.
-- Note: Each database needs its own extensions installed.
-- -----------------------------------------------------------------------------

\c defense_pm_test

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable hierarchical data type
CREATE EXTENSION IF NOT EXISTS ltree;

-- -----------------------------------------------------------------------------
-- Verification (optional - uncomment to see installed extensions)
-- -----------------------------------------------------------------------------
-- SELECT extname, extversion FROM pg_extension;

-- -----------------------------------------------------------------------------
-- Done!
-- -----------------------------------------------------------------------------
-- The databases are now ready:
--   - defense_pm_dev  (development)
--   - defense_pm_test (testing)
--
-- Both have uuid-ossp and ltree extensions enabled.
-- =============================================================================
