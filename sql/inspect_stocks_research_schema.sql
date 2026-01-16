/* ============================================================
   DATABASE & SCHEMA INSPECTION
   Purpose: Discover what tables, columns, and data exist
   Author: No vibes, only facts
   ============================================================ */

---------------------------------------------------------------
-- 0) Confirm database & schema context
---------------------------------------------------------------
SELECT current_database() AS database,
       current_schema()   AS schema,
       current_user       AS user;

---------------------------------------------------------------
-- 1) List ALL schemas (sanity check)
---------------------------------------------------------------
SELECT schema_name
FROM information_schema.schemata
ORDER BY schema_name;

---------------------------------------------------------------
-- 2) List ALL tables in stocks_research schema
---------------------------------------------------------------
SELECT table_schema,
       table_name,
       table_type
FROM information_schema.tables
WHERE table_schema = 'stocks_research'
ORDER BY table_name;

---------------------------------------------------------------
-- 3) Row counts for each stocks_research table
-- (approximate but very useful)
---------------------------------------------------------------
SELECT
    schemaname,
    relname AS table_name,
    n_live_tup AS approx_rows
FROM pg_stat_user_tables
WHERE schemaname = 'stocks_research'
ORDER BY n_live_tup DESC;

---------------------------------------------------------------
-- 4) Column-level inspection for each table
-- (this is the money shot)
---------------------------------------------------------------
SELECT
    table_name,
    ordinal_position,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'stocks_research'
ORDER BY table_name, ordinal_position;

---------------------------------------------------------------
-- 5) Identify tables that *look like fundamentals*
-- (heuristic search by column names)
---------------------------------------------------------------
SELECT DISTINCT table_name
FROM information_schema.columns
WHERE table_schema = 'stocks_research'
  AND (
        column_name ILIKE '%revenue%'
     OR column_name ILIKE '%eps%'
     OR column_name ILIKE '%earn%'
     OR column_name ILIKE '%fiscal%'
     OR column_name ILIKE '%quarter%'
     OR column_name ILIKE '%period%'
     OR column_name ILIKE '%report%'
  )
ORDER BY table_name;

---------------------------------------------------------------
-- 6) For each candidate fundamentals table,
-- show its columns in detail (run AFTER step 5)
---------------------------------------------------------------
-- Replace <TABLE_NAME> with any table found above
-- Example:
-- SELECT *
-- FROM information_schema.columns
-- WHERE table_schema = 'stocks_research'
--   AND table_name = '<TABLE_NAME>'
-- ORDER BY ordinal_position;

---------------------------------------------------------------
-- 7) Identify price tables & adjusted price tables
---------------------------------------------------------------
SELECT DISTINCT table_name
FROM information_schema.columns
WHERE table_schema = 'stocks_research'
  AND (
        column_name ILIKE '%price%'
     OR column_name ILIKE '%close%'
     OR column_name ILIKE '%open%'
     OR column_name ILIKE '%adjust%'
     OR column_name ILIKE '%trade_date%'
  )
ORDER BY table_name;

---------------------------------------------------------------
-- 8) Inspect candidate price tables' key columns
---------------------------------------------------------------
-- Replace <PRICE_TABLE> with suspected adjusted price table
-- Example:
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'stocks_research'
--   AND table_name = '<PRICE_TABLE>'
-- ORDER BY ordinal_position;

---------------------------------------------------------------
-- 9) Sample data from fundamentals-looking tables
-- (LIMITED, safe to run)
---------------------------------------------------------------
-- Replace <TABLE_NAME> accordingly
-- SELECT *
-- FROM stocks_research.<TABLE_NAME>
-- LIMIT 25;

---------------------------------------------------------------
-- 10) Check for FY vs quarterly encoding patterns
-- (very important for Q4 design)
---------------------------------------------------------------
-- Replace <TABLE_NAME> with fundamentals candidate
-- SELECT DISTINCT
--        fiscal_year,
--        fiscal_quarter,
--        period,
--        period_type
-- FROM stocks_research.<TABLE_NAME>
-- LIMIT 50;

---------------------------------------------------------------
-- 11) Identify ingestion / run metadata tables
---------------------------------------------------------------
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'ingestion'
ORDER BY table_name;

---------------------------------------------------------------
-- 12) Inspect ingestion job history (if exists)
---------------------------------------------------------------
-- SELECT *
-- FROM ingestion.ingestion_run
-- ORDER BY started_at DESC
-- LIMIT 20;

---------------------------------------------------------------
-- End of inspection
---------------------------------------------------------------
