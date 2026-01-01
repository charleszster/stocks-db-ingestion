-- Stock Research Schema (PostgreSQL)
-- Defaults locked: trading-day lookbacks; split-adjusted default for momentum features
-- Safe to run in pgAdmin Query Tool.

BEGIN;

-- ----------
-- Core: identity
-- ----------

CREATE TABLE IF NOT EXISTS companies (
  composite_figi   TEXT PRIMARY KEY,
  name             TEXT NOT NULL,
  country          TEXT,
  sector           TEXT,
  industry         TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS securities (
  security_id      BIGSERIAL PRIMARY KEY,
  composite_figi   TEXT NOT NULL REFERENCES companies(composite_figi) ON UPDATE CASCADE ON DELETE RESTRICT,
  primary_exchange TEXT,
  currency         TEXT,
  start_date       DATE,
  end_date         DATE,
  is_active        BOOLEAN NOT NULL DEFAULT TRUE,
  CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

-- Ticker ↔ security mapping over time (identity resolution only)
CREATE TABLE IF NOT EXISTS ticker_history (
  security_id  BIGINT NOT NULL REFERENCES securities(security_id) ON UPDATE CASCADE ON DELETE CASCADE,
  ticker       TEXT   NOT NULL,
  exchange     TEXT   NOT NULL,
  start_date   DATE   NOT NULL,
  end_date     DATE,
  reason       TEXT,
  PRIMARY KEY (security_id, ticker, exchange, start_date),
  CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS ticker_history_lookup_idx
  ON ticker_history (ticker, exchange, start_date, end_date);

-- ----------
-- Core: raw market data (immutable/insert-only by policy)
-- ----------

CREATE TABLE IF NOT EXISTS prices_daily (
  security_id  BIGINT NOT NULL REFERENCES securities(security_id) ON UPDATE CASCADE ON DELETE CASCADE,
  trade_date   DATE   NOT NULL,
  open         NUMERIC(18,6),
  high         NUMERIC(18,6),
  low          NUMERIC(18,6),
  close        NUMERIC(18,6),
  volume       BIGINT,
  PRIMARY KEY (security_id, trade_date),
  CHECK (open IS NULL OR open >= 0),
  CHECK (high IS NULL OR high >= 0),
  CHECK (low  IS NULL OR low  >= 0),
  CHECK (close IS NULL OR close >= 0),
  CHECK (volume IS NULL OR volume >= 0)
);

CREATE INDEX IF NOT EXISTS prices_daily_trade_date_idx
  ON prices_daily (trade_date);

-- Corporate actions: events that affect interpretation (do NOT mutate prices_daily)
CREATE TABLE IF NOT EXISTS corporate_actions (
  security_id  BIGINT NOT NULL REFERENCES securities(security_id) ON UPDATE CASCADE ON DELETE CASCADE,
  action_date  DATE   NOT NULL,
  action_type  TEXT   NOT NULL, -- 'split', 'cash_dividend', 'spin_off', 'merger', etc.
  value_num    NUMERIC,         -- e.g. 2 for 2-for-1 split
  value_den    NUMERIC,         -- e.g. 1 for 2-for-1 split
  cash_amount  NUMERIC,         -- e.g. dividend amount
  currency     TEXT,
  source       TEXT,
  raw_payload  JSONB,
  PRIMARY KEY (security_id, action_date, action_type),
  CHECK (value_den IS NULL OR value_den <> 0)
);

CREATE INDEX IF NOT EXISTS corporate_actions_security_date_idx
  ON corporate_actions (security_id, action_date);

-- Vendor fundamentals (raw, flexible)
CREATE TABLE IF NOT EXISTS fundamentals_quarterly_raw (
  composite_figi TEXT NOT NULL REFERENCES companies(composite_figi) ON UPDATE CASCADE ON DELETE RESTRICT,
  fiscal_period  TEXT NOT NULL,         -- e.g. '2024Q3'
  report_date    DATE,
  metric_name    TEXT NOT NULL,         -- e.g. 'revenue', 'eps_diluted'
  metric_value   NUMERIC,
  source         TEXT,
  raw_payload    JSONB,
  PRIMARY KEY (composite_figi, fiscal_period, metric_name)
);

CREATE INDEX IF NOT EXISTS fundamentals_raw_report_date_idx
  ON fundamentals_quarterly_raw (report_date);

-- ----------
-- Adjustment infrastructure (derived; rebuildable)
-- ----------

-- Split adjustment factors for each security/date
-- split_factor: multiply raw price by split_factor to get split-adjusted price
-- volume_factor: multiply raw volume by volume_factor to get split-adjusted volume
CREATE TABLE IF NOT EXISTS adjustment_factors_daily (
  security_id    BIGINT NOT NULL REFERENCES securities(security_id) ON UPDATE CASCADE ON DELETE CASCADE,
  trade_date     DATE   NOT NULL,
  split_factor   NUMERIC NOT NULL,
  volume_factor  NUMERIC NOT NULL,
  PRIMARY KEY (security_id, trade_date),
  CHECK (split_factor > 0),
  CHECK (volume_factor > 0)
);

CREATE INDEX IF NOT EXISTS adjustment_factors_trade_date_idx
  ON adjustment_factors_daily (trade_date);

-- ----------
-- Research-ready tables (opinionated)
-- ----------

-- The subset of fundamentals you actually use (YoY only, no TTM)
CREATE TABLE IF NOT EXISTS fundamentals_yoy (
  composite_figi  TEXT NOT NULL REFERENCES companies(composite_figi) ON UPDATE CASCADE ON DELETE RESTRICT,
  fiscal_period   TEXT NOT NULL,     -- e.g. '2024Q3'
  revenue_yoy     NUMERIC,
  eps_diluted_yoy NUMERIC,
  is_valid        BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (composite_figi, fiscal_period)
);

-- Feature definitions: parameterized, versioned, immutable identity for derived series
CREATE TABLE IF NOT EXISTS feature_definitions (
  feature_id   BIGSERIAL PRIMARY KEY,
  name         TEXT NOT NULL,     -- e.g. 'return_simple', 'atr'
  parameters   JSONB NOT NULL,    -- includes lookback, adjustment policy, etc.
  version      INTEGER NOT NULL DEFAULT 1,
  code_hash    TEXT NOT NULL,     -- hash of implementation (or git commit SHA)
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_active    BOOLEAN NOT NULL DEFAULT TRUE
);

-- Prevent accidental duplicates for same feature identity
CREATE UNIQUE INDEX IF NOT EXISTS feature_definitions_identity_uniq
  ON feature_definitions (name, version, code_hash, parameters);

-- Daily feature values (long format; append-only by policy)
CREATE TABLE IF NOT EXISTS feature_values_daily (
  feature_id      BIGINT NOT NULL REFERENCES feature_definitions(feature_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  composite_figi  TEXT   NOT NULL REFERENCES companies(composite_figi) ON UPDATE CASCADE ON DELETE RESTRICT,
  trade_date      DATE   NOT NULL,
  value           NUMERIC,
  PRIMARY KEY (feature_id, composite_figi, trade_date)
);

CREATE INDEX IF NOT EXISTS feature_values_feature_date_idx
  ON feature_values_daily (feature_id, trade_date);

CREATE INDEX IF NOT EXISTS feature_values_figi_date_idx
  ON feature_values_daily (composite_figi, trade_date);

-- Universes for research/backtests (eligibility rules stored as JSON)
CREATE TABLE IF NOT EXISTS universes (
  universe_id  BIGSERIAL PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  rules_json   JSONB NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Snapshots: reproducibility boundary for ML/backtests
CREATE TABLE IF NOT EXISTS feature_snapshots (
  snapshot_id    BIGSERIAL PRIMARY KEY,
  snapshot_date  DATE NOT NULL,
  universe_id    BIGINT NOT NULL REFERENCES universes(universe_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  feature_ids    BIGINT[] NOT NULL,
  notes          TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (snapshot_date, universe_id, feature_ids)
);

-- Rankings produced from a snapshot (top N etc.)
CREATE TABLE IF NOT EXISTS rankings_snapshot (
  snapshot_id     BIGINT NOT NULL REFERENCES feature_snapshots(snapshot_id) ON UPDATE CASCADE ON DELETE CASCADE,
  composite_figi  TEXT   NOT NULL REFERENCES companies(composite_figi) ON UPDATE CASCADE ON DELETE RESTRICT,
  rank            INTEGER NOT NULL,
  score           NUMERIC NOT NULL,
  PRIMARY KEY (snapshot_id, composite_figi),
  CHECK (rank > 0)
);

CREATE INDEX IF NOT EXISTS rankings_snapshot_rank_idx
  ON rankings_snapshot (snapshot_id, rank);

COMMIT;
