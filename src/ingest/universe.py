from pathlib import Path
from typing import List
import os
import json
import logging

logger = logging.getLogger(__name__)


def load_tickers() -> List[str]:
    """
    Resolve ticker universe based on UNIVERSE_MODE.
    """
    mode = os.getenv("UNIVERSE_MODE", "explicit").lower()

    if mode == "explicit":
        raw = os.getenv("TICKERS")
        if not raw:
            raise RuntimeError("UNIVERSE_MODE=explicit but TICKERS is not set")

        tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
        if not tickers:
            raise RuntimeError("TICKERS resolved to empty list")

        return tickers

    elif mode == "file":
        repo_root = Path(__file__).resolve().parents[2]
        rel = os.getenv("UNIVERSE_SELECTED", "config/universe_selected.json")
        path = (repo_root / rel).resolve()

        if not path.exists():
            raise RuntimeError(f"Universe selection file not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            tickers = json.load(f)

        if not tickers:
            raise RuntimeError("Universe selection file is empty")

        return tickers

    elif mode == "all":
        # IMPORTANT: do not silently allow this during bootstrap
        return []

    else:
        raise RuntimeError(f"Unknown UNIVERSE_MODE: {mode}")