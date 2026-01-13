-- Phase 4A / 01_extend_adjustment_factors_daily.sql

ALTER TABLE stocks_research.adjustment_factors_daily
ADD COLUMN dividend_factor numeric NOT NULL DEFAULT 1;

ALTER TABLE stocks_research.adjustment_factors_daily
ADD COLUMN price_factor numeric
    GENERATED ALWAYS AS (split_factor * dividend_factor) STORED;

ALTER TABLE stocks_research.adjustment_factors_daily
ADD COLUMN anchor_date date;

UPDATE stocks_research.adjustment_factors_daily
SET anchor_date = trade_date
WHERE anchor_date IS NULL;

ALTER TABLE stocks_research.adjustment_factors_daily
ALTER COLUMN anchor_date SET NOT NULL;

ALTER TABLE stocks_research.adjustment_factors_daily
ADD COLUMN derivation_version text NOT NULL DEFAULT 'v1';

ALTER TABLE stocks_research.adjustment_factors_daily
ADD COLUMN derived_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE stocks_research.adjustment_factors_daily
ADD CONSTRAINT adjustment_factors_daily_dividend_factor_check
CHECK (dividend_factor > 0);
