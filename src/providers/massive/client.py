import os
import requests


class MassiveClient:
    def __init__(self):
        try:
            self.api_key = os.environ["MASSIVE_API_KEY"]
        except KeyError:
            raise RuntimeError(
                "MASSIVE_API_KEY not set in environment. "
                "Ensure .env is loaded before creating MassiveClient."
            )

        self.base_url = "https://api.massive.com/v2"  # adjust if needed

    def get_daily_bars(self, symbol: str) -> list[dict]:
        url = (
            f"{self.base_url}/aggs/ticker/{symbol}/range/1/day/"
            "2021-01-01/2026-01-01"
        )

        params = {
            "adjusted": "false",
            "sort": "asc",
            "limit": 50000,
            "apiKey": self.api_key,
        }

        resp = requests.get(url, params=params, timeout=30)

        resp.raise_for_status()

        payload = resp.json()
        return payload.get("results", [])

