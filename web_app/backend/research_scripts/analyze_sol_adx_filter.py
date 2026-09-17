from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr, _adx

def run_analysis():
    print("Fetching 4 years of 1h data for SOL and BTC...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    sol = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "1h", since=since, limit=100000)
    btc = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=100000)
    
    btc = btc[["timestamp", "close"]].rename(columns={"close": "btc_close"})
    df = pd.merge(sol, btc, on="timestamp", how="left")
    
    df["e200"] = _ema(df["close"], 200)
    df["e20"] = _ema(df["close"], 20)
    df["atr14"] = _atr(df, 14)
    df["v20"] = _sma(df["volume"], 20)
    df["btc_e200"] = _ema(df["btc_close"], 200)
    df["adx14"] = _adx(df, 14)
    
    trades = []
    trades_with_adx = []
    
    # LONG TRADES LOGIC
    last_bullish_cross_idx = 0
    i = 205
    while i < len(df) - 1:
        c = float(df["close"].iloc[i])
        h = float(df["high"].iloc[i])
        l = float(df["low"].iloc[i])
        v = float(df["volume"].iloc[i])
        
        e200_val = float(df["e200"].iloc[i]) if pd.notna(df["e200"].iloc[i]) else 0
        e20_val = float(df["e20"].iloc[i]) if pd.notna(df["e20"].iloc[i]) else 0
        prev_e20 = float(df["e20"].iloc[i-1]) if pd.notna(df["e20"].iloc[i-1]) else 0
        prev_e200 = float(df["e200"].iloc[i-1]) if pd.notna(df["e200"].iloc[i-1]) else 0
        at = float(df["atr14"].iloc[i]) if pd.notna(df["atr14"].iloc[i]) else 0
        v_ma = float(df["v20"].iloc[i]) if pd.notna(df["v20"].iloc[i]) else 0
        btc_c = float(df["btc_close"].iloc[i]) if pd.notna(df["btc_close"].iloc[i]) else 0
        btc_e200_val = float(df["btc_e200"].iloc[i]) if pd.notna(df["btc_e200"].iloc[i]) else 0
        adx_val = float(df["adx14"].iloc[i]) if pd.notna(df["adx14"].iloc[i]) else 0
        
        if prev_e20 <= prev_e200 and e20_val > e200_val:
            last_bullish_cross_idx = i
            
        close_pct = (c - l) / (h - l) if (h - l) > 0 else 0
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        # Original Filters
        if (e20_val > e200_val and 
            20 <= (i - last_bullish_cross_idx) < 150 and 
            l <= e200_val and c > e200_val and 
            close_pct > 0.6 and 
            (v / v_ma) > 1.2 if v_ma > 0 else False and 
            btc_c > btc_e200_val and 
            dt.dayofweek in [1, 2, 3]):
            
            sl = c - 1.5 * at
            tp = c + 15.0 * (c - sl)
            j = i + 1
            exit_idx = None
            result = None
            while j < len(df):
                if float(df["low"].iloc[j]) <= sl:
                    exit_idx, result = j, "LOSS"
                    break
                if float(df["high"].iloc[j]) >= tp:
                    exit_idx, result = j, "WIN"
                    break
                j += 1
            if exit_idx is not None:
                trade_info = {"time": dt, "result": result, "adx": adx_val}
                trades.append(trade_info)
                if adx_val > 25:  # ADX > 25 indicates strong trend
                    trades_with_adx.append(trade_info)
                i = exit_idx
                continue
        i += 1

    print("\n--- ORIGINAL SOL RR 15 (NO ADX FILTER) ---")
    wins = len([t for t in trades if t["result"] == "WIN"])
    losses = len([t for t in trades if t["result"] == "LOSS"])
    total = len(trades)
    wr = wins / total * 100 if total else 0
    net = (wins * 15.0) - losses
    print(f"Trades: {total} | Wins: {wins} | Losses: {losses} | WR: {wr:.2f}% | Profit: {net:+.1f} R")

    print("\n--- SOL RR 15 + ADX > 25 (SIDEWAY FILTER) ---")
    wins_adx = len([t for t in trades_with_adx if t["result"] == "WIN"])
    losses_adx = len([t for t in trades_with_adx if t["result"] == "LOSS"])
    total_adx = len(trades_with_adx)
    wr_adx = wins_adx / total_adx * 100 if total_adx else 0
    net_adx = (wins_adx * 15.0) - losses_adx
    print(f"Trades: {total_adx} | Wins: {wins_adx} | Losses: {losses_adx} | WR: {wr_adx:.2f}% | Profit: {net_adx:+.1f} R")
    
    print("\nTrades filtered out by ADX:")
    filtered_out = [t for t in trades if t["adx"] <= 25]
    for t in filtered_out:
        print(f"Date: {t['time'].strftime('%Y-%m-%d')} | ADX: {t['adx']:.1f} | Result: {t['result']}")

if __name__ == "__main__":
    run_analysis()
