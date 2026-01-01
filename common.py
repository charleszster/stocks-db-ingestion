from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import os
import time
from datetime import date, timedelta
from typing import Any, Dict, Optional

import requests


def getenv(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def requests_get_json(url: str, params: Dict[str, Any], api_key: str, max_retries: int = 6) -> Dict[str, Any]:
    """GET JSON with basic retry/backoff for rate limits and transient errors."""
    headers = {"Authorization": f"Bearer {api_key}"}
    backoff = 1.0
    last_err = None

    for _ in range(max_retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=30)
            if r.status_code == 429:
                ra = r.headers.get("Retry-After")
                sleep_s = float(ra) if ra else backoff
                time.sleep(sleep_s)
                backoff = min(backoff * 2, 30.0)
                continue
            if 500 <= r.status_code < 600:
                time.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)

    raise RuntimeError(f"Failed after retries. url={url} params={params} last_err={last_err}")


def iso_today() -> str:
    return date.today().isoformat()


def iso_years_ago(years: int) -> str:
    return (date.today() - timedelta(days=365 * years)).isoformat()
