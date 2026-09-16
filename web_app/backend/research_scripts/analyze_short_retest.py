from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def run_analysis():
    print("Fetching 4 years of 1h data for SOL and BTC (SHORT TEST)...")
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
    
    trades = []
    i = 205
    last_bearish_cross_idx = 0
    rr_target = 15.0
    
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
        
        # Bearish Cross (Fast drops below Slow)
        if prev_e20 >= prev_e200 and e20_val < e200_val:
            last_bearish_cross_idx = i
            
        candle_range = h - l
        # Close pct for SHORT: 0 means close at the low (strong bearish), 1 means close at the high
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        # SHORT FILTERS
        is_downtrend = e20_val < e200_val
        candles_since_cross = i - last_bearish_cross_idx
        is_proper_speed = 20 <= candles_since_cross < 150
        is_touching = h >= e200_val and c < e200_val  # Price wicked up to EMA 200
        is_strong_rejection = close_pct < 0.4  # Closed in the BOTTOM 40% (Bearish pinbar)
        
        has_volume = (v / v_ma) > 1.2 if v_ma > 0 else False
        btc_bearish = btc_c < btc_e200_val
        is_midweek = dt.dayofweek in [1, 2, 3] # Tue, Wed, Thu
        
        if is_downtrend and is_proper_speed and is_touching and is_strong_rejection and has_volume and btc_bearish and is_midweek:
            entry = c
            # SL is ABOVE the entry for Shorts
            sl = entry + 1.5 * at
            
            risk = sl - entry
            if risk > 0:
                # TP is BELOW the entry for Shorts
                tp = entry - rr_target * risk
                
                j = i + 1
                exit_idx = None
                result = None
                
                while j < len(df):
                    hi = float(df["high"].iloc[j])
                    lo = float(df["low"].iloc[j])
                    
                    # For Short: If High hits SL first -> LOSS. If Low hits TP first -> WIN.
                    if hi >= sl: exit_idx, result = j, "LOSS"; break
                    if lo <= tp: exit_idx, result = j, "WIN"; break
                    j += 1
                    
                if exit_idx is not None:
                    exit_dt = pd.to_datetime(df["timestamp"].iloc[exit_idx], utc=True)
                    trades.append({
                        "entry_time": dt,
                        "exit_time": exit_dt,
                        "result": result
                    })
                    i = exit_idx
                    continue
        i += 1

    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    total = len(trades)
    wr = len(wins) / total * 100 if total else 0
    net = (len(wins) * rr_target) - len(losses)
    
    print(f"\n--- SOLANA SHORT (BEAR MARKET) RETEST RR {rr_target} ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {len(wins)}")
    print(f"Losses: {len(losses)}")
    print(f"Winrate: {wr:.2f}%")
    print(f"Net Profit: {net:+.1f}R\n")
    
    # Let's sweep the RR just to see if shorts behave differently
    print("--- SWEEPING RR FOR SHORTS ---")
    rr_sweep = [2.0, 3.0, 5.0, 7.0, 10.0, 15.0]
    for rrt in rr_sweep:
        w_cnt = 0
        l_cnt = 0
        skip_idx = 0
        
        # We need to re-simulate exactly for sweep because exit indices change based on RR
        for i_entry in range(205, len(df)-1):
            if i_entry < skip_idx: continue
            
            c = float(df["close"].iloc[i_entry])
            h = float(df["high"].iloc[i_entry])
            l = float(df["low"].iloc[i_entry])
            v = float(df["volume"].iloc[i_entry])
            
            e200_val = float(df["e200"].iloc[i_entry]) if pd.notna(df["e200"].iloc[i_entry]) else 0
            e20_val = float(df["e20"].iloc[i_entry]) if pd.notna(df["e20"].iloc[i_entry]) else 0
            prev_e20 = float(df["e20"].iloc[i_entry-1]) if pd.notna(df["e20"].iloc[i_entry-1]) else 0
            prev_e200 = float(df["e200"].iloc[i_entry-1]) if pd.notna(df["e200"].iloc[i_entry-1]) else 0
            at = float(df["atr14"].iloc[i_entry]) if pd.notna(df["atr14"].iloc[i_entry]) else 0
            v_ma = float(df["v20"].iloc[i_entry]) if pd.notna(df["v20"].iloc[i_entry]) else 0
            btc_c = float(df["btc_close"].iloc[i_entry]) if pd.notna(df["btc_close"].iloc[i_entry]) else 0
            btc_e200_val = float(df["btc_e200"].iloc[i_entry]) if pd.notna(df["btc_e200"].iloc[i_entry]) else 0
            
            if prev_e20 >= prev_e200 and e20_val < e200_val:
                last_bearish_cross_idx = i_entry
                
            candle_range = h - l
            close_pct = (c - l) / candle_range if candle_range > 0 else 0
            dt = pd.to_datetime(df["timestamp"].iloc[i_entry], utc=True)
            
            is_downtrend = e20_val < e200_val
            is_proper_speed = 20 <= (i_entry - last_bearish_cross_idx) < 150
            is_touching = h >= e200_val and c < e200_val
            is_strong_rejection = close_pct < 0.4
            has_volume = (v / v_ma) > 1.2 if v_ma > 0 else False
            btc_bearish = btc_c < btc_e200_val
            is_midweek = dt.dayofweek in [1, 2, 3]
            
            if is_downtrend and is_proper_speed and is_touching and is_strong_rejection and has_volume and btc_bearish and is_midweek:
                entry = c
                sl = entry + 1.5 * at
                risk = sl - entry
                if risk > 0:
                    tp = entry - rrt * risk
                    j = i_entry + 1
                    exit_idx = None
                    result = None
                    while j < len(df):
                        hi = float(df["high"].iloc[j])
                        lo = float(df["low"].iloc[j])
                        if hi >= sl: exit_idx, result = j, "LOSS"; break
                        if lo <= tp: exit_idx, result = j, "WIN"; break
                        j += 1
                        
                    if exit_idx is not None:
                        if result == "WIN": w_cnt += 1
                        else: l_cnt += 1
                        skip_idx = exit_idx
        
        tot = w_cnt + l_cnt
        wr = w_cnt / tot * 100 if tot else 0
        net = (w_cnt * rrt) - l_cnt
        print(f"RR: {rrt:>4.1f} | Trades: {tot:>2} | Wins: {w_cnt:>2} | Losses: {l_cnt:>2} | WR: {wr:05.2f}% | Profit: {net:>+6.1f}R")

if __name__ == "__main__":
    run_analysis()
