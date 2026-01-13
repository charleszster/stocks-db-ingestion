-- Phase 4A / 02_create_adjustment_events.sql

CREATE TABLE stocks_research.adjustment_events (
    security_id bigint NOT NULL,
    corporate_action_id bigint NOT NULL,
    action_type text NOT NULL,

    effective_ts timestamptz NOT NULL,

    split_price_mult numeric NOT NULL DEFAULT 1,
    dividend_price_mult numeric NOT NULL DEFAULT 1,
    price_mult numeric NOT NULL,

    prev_close_date date,
    prev_close numeric,

    resolution_status text NOT NULL,
    derivation_version text NOT NULL,
    derived_at timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (security_id, corporate_action_id),

    CONSTRAINT adjustment_events_security_fk
        FOREIGN KEY (security_id)
        REFERENCES stocks_research.securities(security_id)
        ON DELETE CASCADE
);
