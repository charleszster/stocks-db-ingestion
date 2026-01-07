BOOTSTRAP
---------
00_bootstrap_universe.py
  creates: companies, securities, ticker_history

INGESTION
---------
prices_daily.py
  requires: securities, ticker_history
  writes: prices_daily

corporate_actions.py
  requires: securities, ticker_history
  writes: corporate_actions
