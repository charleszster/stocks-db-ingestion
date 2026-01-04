from dataclasses import dataclass
from datetime import date
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class DailyBar:
    symbol: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    vwap: Optional[Decimal]
    trades: Optional[int]


from datetime import datetime
from decimal import Decimal

from .client import MassiveClient


def fetch_daily(symbol: str) -> list[DailyBar]:
    client = MassiveClient()   # instantiate lazily, after dotenv load
    raw_rows = client.get_daily_bars(symbol)

    bars: list[DailyBar] = []

    for row in raw_rows:
        bars.append(
            DailyBar(
                symbol=symbol,
                trade_date=datetime.fromtimestamp(
                    row["t"] / 1000, tz=timezone.utc
                ).date(),
                open=Decimal(str(row["o"])),
                high=Decimal(str(row["h"])),
                low=Decimal(str(row["l"])),
                close=Decimal(str(row["c"])),
                volume=int(row["v"]),
                vwap=Decimal(str(row["vw"])) if "vw" in row else None,
                trades=int(row["n"]) if "n" in row else None,
            )
        )

    return bars

