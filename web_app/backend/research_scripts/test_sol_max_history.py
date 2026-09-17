from datetime import datetime, timedelta, timezone
import pandas as pd
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def run_analysis():
    print("Fetching ALL AVAILABLE 1h data for SOL and BTC...")
    # Go back 3000 days (approx 8.2 years) - this will just fetch from the beginning of the coin's listing
    since = datetime.now(timezone.utc) - timedelta(days=3000)
    
    sol = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "1h", since=since, limit=200000)
    btc = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=200000)
    
    btc = btc[["timestamp", "close"]].rename(columns={"close": "btc_close"})
    df = pd.merge(sol, btc, on="timestamp", how="left")
    
    start_date = df['timestamp'].iloc[0].strftime('%Y-%m-%d')
    end_date = df['timestamp'].iloc[-1].strftime('%Y-%m-%d')
    total_days = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days
    print(f"Data from {start_date} to {end_date} ({total_days} days | ~{total_days/365:.1f} years)")
    
    df["e200"] = _ema(df["close"], 200)
    df["e20"] = _ema(df["close"], 20)
    df["atr14"] = _atr(df, 14)
    df["v20"] = _sma(df["volume"], 20)
    df["btc_e200"] = _ema(df["btc_close"], 200)
    
    trades = []
    
    # 1. LONG TRADES
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
        
        if prev_e20 <= prev_e200 and e20_val > e200_val:
            last_bullish_cross_idx = i
            
        close_pct = (c - l) / (h - l) if (h - l) > 0 else 0
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
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
                trades.append({"type": "LONG", "result": result, "year": dt.year})
                i = exit_idx
                continue
        i += 1
        
    # 2. SHORT TRADES
    last_bearish_cross_idx = 0
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
        
        if prev_e20 >= prev_e200 and e20_val < e200_val:
            last_bearish_cross_idx = i
            
        close_pct = (c - l) / (h - l) if (h - l) > 0 else 0
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        if (e20_val < e200_val and 
            20 <= (i - last_bearish_cross_idx) < 150 and 
            h >= e200_val and c < e200_val and 
            close_pct < 0.4 and 
            (v / v_ma) > 1.2 if v_ma > 0 else False and 
            btc_c < btc_e200_val and 
            dt.dayofweek in [1, 2, 3]):
            
            sl = c + 1.5 * at
            tp = c - 15.0 * (sl - c)
            j = i + 1
            exit_idx = None
            result = None
            while j < len(df):
                if float(df["high"].iloc[j]) >= sl:
                    exit_idx, result = j, "LOSS"
                    break
                if float(df["low"].iloc[j]) <= tp:
                    exit_idx, result = j, "WIN"
                    break
                j += 1
            if exit_idx is not None:
                trades.append({"type": "SHORT", "result": result, "year": dt.year})
                i = exit_idx
                continue
        i += 1

    print("\n--- SOLANA RETEST RR 15.0 (ALL TIME HISTORY) ---")
    longs = [t for t in trades if t["type"] == "LONG"]
    shorts = [t for t in trades if t["type"] == "SHORT"]
    
    for label, subset in [("LONG", longs), ("SHORT", shorts), ("TOTAL", trades)]:
        wins = len([t for t in subset if t["result"] == "WIN"])
        losses = len([t for t in subset if t["result"] == "LOSS"])
        total = len(subset)
        wr = wins / total * 100 if total else 0
        net = (wins * 15.0) - losses
        print(f"\n[{label}] Trades: {total} | Wins: {wins} | Losses: {losses} | WR: {wr:.2f}% | Profit: {net:+.1f} R")

if __name__ == "__main__":
    run_analysis()
