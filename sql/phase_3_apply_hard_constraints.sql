BEGIN;

-- ============================================================
-- Phase 3 HARD Constraints
-- Revised to match actual schema
-- ============================================================

-- Required for exclusion constraints using equality + ranges
CREATE EXTENSION IF NOT EXISTS btree_gist;


-- ============================================================
-- 1. companies
-- ============================================================

ALTER TABLE stocks_research.companies
ADD CONSTRAINT companies_composite_figi_uniq
UNIQUE (composite_figi);


-- ============================================================
-- 2. securities
-- ============================================================

-- Enforce one-to-one mapping between security and composite_figi
ALTER TABLE stocks_research.securities
ADD CONSTRAINT securities_composite_figi_uniq
UNIQUE (composite_figi);

-- Enforce valid security lifecycle dates
ALTER TABLE stocks_research.securities
ADD CONSTRAINT securities_date_order_chk
CHECK (end_date IS NULL OR end_date >= start_date);


-- ============================================================
-- 3. ticker_history
-- ============================================================

-- Enforce valid ticker lifecycle dates
ALTER TABLE stocks_research.ticker_history
ADD CONSTRAINT ticker_history_date_order_chk
CHECK (end_date IS NULL OR end_date >= start_date);

-- Prevent overlapping ticker ranges per security
ALTER TABLE stocks_research.ticker_history
ADD CONSTRAINT ticker_history_no_overlap_per_security
EXCLUDE USING gist (
    security_id WITH =,
    daterange(start_date, COALESCE(end_date, 'infinity'::date)) WITH &&
);

-- Prevent overlapping reuse of (exchange, ticker) across securities
ALTER TABLE stocks_research.ticker_history
ADD CONSTRAINT ticker_history_no_overlap_exchange_ticker
EXCLUDE USING gist (
    exchange WITH =,
    ticker WITH =,
    daterange(start_date, COALESCE(end_date, 'infinity'::date)) WITH &&
);


-- ============================================================
-- 4. prices_daily
-- ============================================================

-- Enforce OHLC sanity
ALTER TABLE stocks_research.prices_daily
ADD CONSTRAINT prices_daily_high_low_chk
CHECK (high >= low);

-- Enforce non-negative volume
ALTER TABLE stocks_research.prices_daily
ADD CONSTRAINT prices_daily_volume_chk
CHECK (volume >= 0);


-- ============================================================
-- Phase 3 HARD Constraints COMPLETE
-- ============================================================

COMMIT;
