from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def test_sol_retest_filtered():
    print("Fetching 4 years of 1h data for SOL/USDT...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "1h", since=since, limit=100000)
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    e200 = _ema(close, 200)
    e20 = _ema(close, 20)
    atr14 = _atr(df, 14)
    v20 = _sma(vol, 20)
    
    trades = []
    i = 205
    last_bullish_cross_idx = 0
    rr_target = 10.0
    
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        
        e200_val = float(e200.iloc[i]) if pd.notna(e200.iloc[i]) else 0
        e20_val = float(e20.iloc[i]) if pd.notna(e20.iloc[i]) else 0
        prev_e20 = float(e20.iloc[i-1]) if pd.notna(e20.iloc[i-1]) else 0
        prev_e200 = float(e200.iloc[i-1]) if pd.notna(e200.iloc[i-1]) else 0
        at = float(atr14.iloc[i]) if pd.notna(atr14.iloc[i]) else 0
        v_ma = float(v20.iloc[i]) if pd.notna(v20.iloc[i]) else 0
        
        if prev_e20 <= prev_e200 and e20_val > e200_val:
            last_bullish_cross_idx = i
            
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        
        # FILTERS
        is_uptrend = e20_val > e200_val
        candles_since_cross = i - last_bullish_cross_idx
        
        # New optimal parameters
        is_proper_speed = 20 <= candles_since_cross < 150
        is_strong_rejection = close_pct > 0.6
        has_volume = (v / v_ma) > 1.2 if v_ma > 0 else False
        
        is_touching = l <= e200_val and c > e200_val
        
        if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and has_volume:
            entry = c
            sl = entry - 1.5 * at
            
            risk = entry - sl
            if risk > 0:
                tp = entry + rr_target * risk
                
                j = i + 1
                exit_idx = None
                result = None
                
                while j < len(df):
                    hi = float(high.iloc[j])
                    lo = float(low.iloc[j])
                    if lo <= sl: exit_idx, result = j, "LOSS"; break
                    if hi >= tp: exit_idx, result = j, "WIN"; break
                    j += 1
                    
                if exit_idx is not None:
                    trades.append(result)
                    i = exit_idx
                    continue
        i += 1
        
    wins = trades.count("WIN")
    losses = trades.count("LOSS")
    total = len(trades)
    wr = wins / total * 100 if total else 0
    net_r = (wins * rr_target) - (losses * 1.0)
    
    print("\n--- 🚀 SOLANA 1H SMC RETEST (FILTERED) RR = 5.0 ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Winrate: {wr:.2f}%")
    print(f"Net Profit: +{net_r:.2f}R")

if __name__ == "__main__":
    test_sol_retest_filtered()
