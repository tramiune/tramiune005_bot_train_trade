"""Download Binance USD-M FUTURES klines from the official bulk archive (data.binance.vision),
verify every file against its published SHA256 checksum, and cache them as one .npz per symbol/interval.

Usage (local machine, repo root):
    web_app/backend/.venv/bin/python .agents/skills/honest-backtest/scripts/bt_data.py DOGEUSDT 1m 2022-09
Data lands in data/futures_um/ (gitignored).
"""
import datetime as dt
import hashlib
import io
import os
import sys
import urllib.error
import urllib.request
import zipfile

import numpy as np
import pandas as pd

BASE = "https://data.binance.vision/data/futures/um"
ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "futures_um")
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume",
        "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def _fetch_zip(url):
    """Return the CSV DataFrame inside the zip, or None if the file does not exist (404)."""
    try:
        blob = _get(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    expected = _get(url + ".CHECKSUM").decode().split()[0]
    got = hashlib.sha256(blob).hexdigest()
    assert got == expected, f"checksum mismatch for {url}"
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        raw = z.read(z.namelist()[0]).decode()
    first = raw.split("\n", 1)[0]
    has_header = not first.split(",")[0].strip().isdigit()
    df = pd.read_csv(io.StringIO(raw), header=0 if has_header else None)
    df.columns = COLS
    return df


def download(symbol, interval, start_month):
    os.makedirs(ROOT, exist_ok=True)
    out = os.path.join(ROOT, f"{symbol}_{interval}.npz")
    today = dt.date.today()
    y, m = map(int, start_month.split("-"))
    parts, month = [], dt.date(y, m, 1)
    last_full_month = None
    while month < dt.date(today.year, today.month, 1):
        tag = month.strftime("%Y-%m")
        df = _fetch_zip(f"{BASE}/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{tag}.zip")
        if df is None:
            print(f"  {tag}: not published (yet)", flush=True)
            break
        parts.append(df); last_full_month = month
        print(f"  {tag}: {len(df)} rows ok", flush=True)
        month = (month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    # daily files for the rest (current month / month not yet published as monthly)
    day = month
    while day < today:
        tag = day.strftime("%Y-%m-%d")
        df = _fetch_zip(f"{BASE}/daily/klines/{symbol}/{interval}/{symbol}-{interval}-{tag}.zip")
        if df is not None:
            parts.append(df); print(f"  {tag}: {len(df)} rows ok (daily)", flush=True)
        day += dt.timedelta(days=1)
    df = pd.concat(parts, ignore_index=True)
    df = df.drop_duplicates("open_time").sort_values("open_time")
    t = (df["open_time"].to_numpy() // 1000).astype(np.int64)  # seconds
    np.savez_compressed(out, time=t, **{k: df[k].to_numpy(dtype=np.float64) for k in
                                         ("open", "high", "low", "close", "volume", "taker_buy_volume")})
    print(f"saved {out}: {len(df)} candles {pd.to_datetime(t[0], unit='s')} -> {pd.to_datetime(t[-1], unit='s')}")
    return out


def load(symbol, interval):
    """Load cached futures klines as a DataFrame with columns time(sec), open, high, low, close, volume."""
    z = np.load(os.path.join(ROOT, f"{symbol}_{interval}.npz"))
    return pd.DataFrame({k: z[k] for k in z.files})


if __name__ == "__main__":
    download(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "2022-09")
