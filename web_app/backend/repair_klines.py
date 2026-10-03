"""Rebuild the stored 3m DOGEUSDT candles from Binance USD-M FUTURES.

Usage (run from web_app/backend):
    python repair_klines.py download   # fetch clean futures candles into repaired_klines.db (bot can keep running)
    python repair_klines.py report     # compare trading_bot.db against the clean copy (read-only)
    python repair_klines.py apply      # replace the table in trading_bot.db (STOP the backend first; makes a backup)

Only fully CLOSED candles are kept. Data comes straight from https://fapi.binance.com (public, no key).
"""
import json
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.request

LIVE_DB = "trading_bot.db"
CLEAN_DB = "repaired_klines.db"
TABLE = "klines_dogeusdt_3m"
SYMBOL, INTERVAL, STEP = "DOGEUSDT", "3m", 180
URL = "https://fapi.binance.com/fapi/v1/klines?symbol=%s&interval=%s&startTime=%d&limit=1500"


def fetch(start_ms):
    for attempt in range(6):
        try:
            with urllib.request.urlopen(URL % (SYMBOL, INTERVAL, start_ms), timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            wait = 30 if e.code in (418, 429) else 3
            print(f"  HTTP {e.code}, waiting {wait}s (attempt {attempt + 1})")
            time.sleep(wait)
        except Exception as e:
            print(f"  {type(e).__name__}: {e}, retrying")
            time.sleep(3)
    raise RuntimeError("Binance fapi kept failing")


def download():
    live = sqlite3.connect(LIVE_DB)
    first = live.execute(f"SELECT MIN(time) FROM {TABLE}").fetchone()[0]
    live.close()
    out = sqlite3.connect(CLEAN_DB)
    out.execute(f"DROP TABLE IF EXISTS {TABLE}")
    out.execute(f"CREATE TABLE {TABLE} (time INTEGER PRIMARY KEY, open REAL, high REAL, low REAL, close REAL, volume REAL)")
    start_ms, total = first * 1000, 0
    while True:
        rows = fetch(start_ms)
        if not rows:
            break
        now_ms = int(time.time() * 1000)
        closed = [r for r in rows if r[0] + STEP * 1000 <= now_ms]  # closed candles only
        out.executemany(
            f"INSERT OR REPLACE INTO {TABLE} VALUES (?,?,?,?,?,?)",
            [(int(r[0] / 1000), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])) for r in closed],
        )
        total += len(closed)
        start_ms = rows[-1][0] + 1
        if total % 30000 < 1500:
            print(f"  downloaded {total} candles...")
            out.commit()
        if len(closed) < len(rows) or len(rows) < 1500:
            break
        time.sleep(0.3)  # stay well under the request-weight limit
    out.commit()
    n, mn, mx = out.execute(f"SELECT COUNT(*), MIN(time), MAX(time) FROM {TABLE}").fetchone()
    print(f"Clean copy ready: {n} candles, {mn} -> {mx}")
    out.close()


def report():
    live = sqlite3.connect(LIVE_DB)
    live.execute(f"ATTACH DATABASE '{CLEAN_DB}' AS clean")
    q = lambda sql: live.execute(sql).fetchone()[0]
    total = q(f"SELECT COUNT(*) FROM main.{TABLE}")
    dup_ts = q(f"SELECT COUNT(*) FROM (SELECT time FROM main.{TABLE} GROUP BY time HAVING COUNT(*) > 1)")
    wrong = q(f"""SELECT COUNT(*) FROM (SELECT DISTINCT m.time FROM main.{TABLE} m JOIN clean.{TABLE} c ON c.time = m.time
                 WHERE ABS(m.open-c.open) > 1e-9 OR ABS(m.high-c.high) > 1e-9 OR ABS(m.low-c.low) > 1e-9 OR ABS(m.close-c.close) > 1e-9)""")
    missing = q(f"SELECT COUNT(*) FROM clean.{TABLE} WHERE time NOT IN (SELECT time FROM main.{TABLE})")
    extra = q(f"SELECT COUNT(*) FROM (SELECT DISTINCT time FROM main.{TABLE}) WHERE time NOT IN (SELECT time FROM clean.{TABLE})")
    print(f"stored rows: {total}\nduplicated timestamps: {dup_ts}\ncandles with wrong OHLC vs Futures: {wrong}\n"
          f"candles missing from stored data: {missing}\nstored candles not in Futures data (e.g. unfinished): {extra}")


def apply():
    backup = f"{LIVE_DB}.bak-{int(time.time())}"
    shutil.copy(LIVE_DB, backup)
    print(f"Backup written: {backup}")
    live = sqlite3.connect(LIVE_DB)
    live.execute(f"ATTACH DATABASE '{CLEAN_DB}' AS clean")
    with live:
        live.execute(f"DROP TABLE IF EXISTS main.{TABLE}")
        live.execute(f"CREATE TABLE main.{TABLE} (time INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL)")
        live.execute(f"INSERT INTO main.{TABLE} SELECT time, open, high, low, close, volume FROM clean.{TABLE} ORDER BY time")
        live.execute(f"CREATE UNIQUE INDEX uq_{TABLE}_time ON {TABLE} (time)")
    n = live.execute(f"SELECT COUNT(*) FROM main.{TABLE}").fetchone()[0]
    print(f"Applied. {TABLE} now has {n} clean Futures candles.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"download": download, "report": report, "apply": apply}.get(cmd, lambda: print(__doc__))()
