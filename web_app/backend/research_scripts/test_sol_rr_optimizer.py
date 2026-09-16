from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def run_optimizer():
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
    
    # Pre-calculate entry signals
    entries = []
    i = 205
    last_bullish_cross_idx = 0
    
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
        
        is_uptrend = e20_val > e200_val
        candles_since_cross = i - last_bullish_cross_idx
        is_proper_speed = 20 <= candles_since_cross < 150
        is_strong_rejection = close_pct > 0.6
        has_volume = (v / v_ma) > 1.2 if v_ma > 0 else False
        is_touching = l <= e200_val and c > e200_val
        
        if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and has_volume:
            entries.append((i, c, at))
            # Note: We don't skip ahead here because skipping depends on how long the trade takes (which depends on RR).
            # We will handle overlapping trades inside the simulation loop.
        i += 1
        
    print(f"Found {len(entries)} raw entry signals.")
    
    rr_targets = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0, 15.0]
    
    print("\n--- SOLANA 1H SMC RETEST RR OPTIMIZER ---")
    
    for rr in rr_targets:
        wins = 0
        losses = 0
        skip_until = 0
        
        for entry_idx, entry, at in entries:
            if entry_idx < skip_until:
                continue
                
            sl = entry - 1.5 * at
            risk = entry - sl
            if risk <= 0: continue
            
            tp = entry + rr * risk
            
            j = entry_idx + 1
            exit_idx = None
            result = None
            
            while j < len(df):
                hi = float(high.iloc[j])
                lo = float(low.iloc[j])
                if lo <= sl: exit_idx, result = j, "LOSS"; break
                if hi >= tp: exit_idx, result = j, "WIN"; break
                j += 1
                
            if exit_idx is not None:
                if result == "WIN": wins += 1
                elif result == "LOSS": losses += 1
                skip_until = exit_idx
                
        total = wins + losses
        if total > 0:
            winrate = wins / total * 100
            net_profit = (wins * rr) - losses
            print(f"RR: {rr:>4.1f} | Trades: {total:>3} | Wins: {wins:>3} | Losses: {losses:>3} | WR: {winrate:05.2f}% | Profit: {net_profit:>+6.1f}R")

if __name__ == "__main__":
    run_optimizer()
