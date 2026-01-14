-- Phase 4A: Adjusted daily prices view
-- Raw prices remain immutable in stocks_research.prices_daily
-- Price adjustment uses price_factor from adjustment_factors_daily

CREATE OR REPLACE VIEW stocks_research.prices_daily_adjusted_v AS
SELECT
    p.security_id,
    p.trade_date,

    -- raw prices
    p.open,
    p.high,
    p.low,
    p.close,
    p.volume,

    -- adjustment metadata
    f.price_factor     AS adj_price_factor,
    f.split_factor,
    f.dividend_factor,
    f.volume_factor,
    f.anchor_date,
    f.derivation_version,
    f.derived_at,

    -- adjusted prices
    (p.open  * f.price_factor) AS adj_open,
    (p.high  * f.price_factor) AS adj_high,
    (p.low   * f.price_factor) AS adj_low,
    (p.close * f.price_factor) AS adj_close

FROM stocks_research.prices_daily p
JOIN stocks_research.adjustment_factors_daily f
  ON f.security_id = p.security_id
 AND f.trade_date  = p.trade_date;
