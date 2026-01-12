from pathlib import Path
from typing import List
import os
import json


def load_tickers() -> List[str]:
    """
    Load the selected universe produced by bootstrap.
    """
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
