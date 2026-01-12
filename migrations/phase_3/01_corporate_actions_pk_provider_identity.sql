BEGIN;

-- Align identity with provider truth:
-- canonical identity is (provider, provider_action_id)
ALTER TABLE stocks_research.corporate_actions
  DROP CONSTRAINT IF EXISTS corporate_actions_pkey;

ALTER TABLE stocks_research.corporate_actions
  ADD CONSTRAINT corporate_actions_pkey
  PRIMARY KEY (provider, provider_action_id);

-- Remove any redundant uniqueness index if it exists
DROP INDEX IF EXISTS stocks_research.corporate_actions_provider_uidx;

-- Legacy uniqueness is invalid for dividends (same-day multi-events)
DROP INDEX IF EXISTS stocks_research.corporate_actions_legacy_uidx;

COMMIT;
