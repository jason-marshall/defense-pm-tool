-- Enable ltree extension for WBS hierarchy
CREATE EXTENSION IF NOT EXISTS ltree;

-- Create test database
CREATE DATABASE defense_pm_test;
GRANT ALL PRIVILEGES ON DATABASE defense_pm_test TO dev_user;

-- Connect to test database and enable ltree
\c defense_pm_test
CREATE EXTENSION IF NOT EXISTS ltree;