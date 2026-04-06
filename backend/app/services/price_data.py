import asyncio
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
import yfinance as yf

from app.models.instrument_universe import INSTRUMENTS

BINANCE_BASE = "https://api.binance.com"
_executor = ThreadPoolExecutor(max_workers=10)

_session = requests.Session()
adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=Retry(total=2, backoff_factor=0.5))
_session.mount("https://", adapter)
_session.mount("http://", adapter)


def _yahoo_to_standard(df: pd.DataFrame) -> list[dict]:
    records = []
    for idx, row in df.iterrows():
        vol = row.get("Volume", 0)
        if pd.isna(vol):
            vol = 0
        records.append({
            "snapshotTime": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
            "openPrice": {"bid": float(row.get("Open", 0)), "ask": float(row.get("Open", 0))},
            "highPrice": {"bid": float(row.get("High", 0)), "ask": float(row.get("High", 0))},
            "lowPrice": {"bid": float(row.get("Low", 0)), "ask": float(row.get("Low", 0))},
            "closePrice": {"bid": float(row.get("Close", 0)), "ask": float(row.get("Close", 0))},
            "lastTradedVolume": int(vol),
        })
    return records


def fetch_yahoo(ticker: str, resolution: str = "1d") -> list[dict]:
    period_map = {"1d": "6mo", "4h": "60d", "1h": "60d", "15m": "60d"}
    interval_map = {"1d": "1d", "4h": "1h", "1h": "1h", "15m": "15m"}
    period = period_map.get(resolution, "6mo")
    interval = interval_map.get(resolution, "1d")

    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period=period, interval=interval)
        if df.empty:
            return []
        if resolution == "4h" and len(df) >= 4:
            df = df.resample("4h").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum",
            }).dropna()
        return _yahoo_to_standard(df)
    except Exception as e:
        print(f"Yahoo fetch error for {ticker}: {e}")
        return []


def fetch_binance(symbol: str, interval: str = "1d", limit: int = 200) -> list[dict]:
    interval_map = {"1d": "1d", "4h": "4h", "1h": "1h", "15m": "15m"}
    bn_interval = interval_map.get(interval, "1d")
    try:
        resp = _session.get(
            f"{BINANCE_BASE}/api/v3/klines",
            params={"symbol": symbol, "interval": bn_interval, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        records = []
        for k in data:
            records.append({
                "snapshotTime": datetime.utcfromtimestamp(k[0] / 1000).isoformat(),
                "openPrice": {"bid": float(k[1]), "ask": float(k[1])},
                "highPrice": {"bid": float(k[2]), "ask": float(k[2])},
                "lowPrice": {"bid": float(k[3]), "ask": float(k[3])},
                "closePrice": {"bid": float(k[4]), "ask": float(k[4])},
                "lastTradedVolume": int(float(k[5])),
            })
        return records
    except Exception as e:
        print(f"Binance fetch error for {symbol}: {e}")
        return []


def fetch_prices(instrument: dict, resolution: str = "1d") -> list[dict]:
    binance_sym = instrument.get("binance")
    if binance_sym:
        return fetch_binance(binance_sym, resolution)
    return fetch_yahoo(instrument["yahoo"], resolution)


async def fetch_prices_async(instrument: dict, resolution: str = "1d") -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fetch_prices, instrument, resolution)


def fetch_current_price(instrument: dict) -> float | None:
    binance_sym = instrument.get("binance")
    if binance_sym:
        try:
            resp = requests.get(f"{BINANCE_BASE}/api/v3/ticker/price", params={"symbol": binance_sym}, timeout=5)
            return float(resp.json()["price"])
        except Exception:
            pass
    try:
        tk = yf.Ticker(instrument["yahoo"])
        df = tk.history(period="1d", interval="1m")
        if not df.empty:
            return float(df["Close"].iloc[-1])
    except Exception:
        pass
    return None


def prices_to_df(prices: list[dict]) -> pd.DataFrame:
    if not prices:
        return pd.DataFrame()
    rows = []
    for p in prices:
        rows.append({
            "datetime": p["snapshotTime"],
            "open": p["openPrice"]["bid"],
            "high": p["highPrice"]["bid"],
            "low": p["lowPrice"]["bid"],
            "close": p["closePrice"]["bid"],
            "volume": p["lastTradedVolume"],
        })
    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df.set_index("datetime", inplace=True)
    df = df.astype(float)
    return df
