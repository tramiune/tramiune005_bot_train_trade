from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def test_5m():
    print("Fetching 1 year of 5m data for ETH/USDT Sniper (SL 0.5%, TP 10%)...")
    since = datetime.now(timezone.utc) - timedelta(days=365)
    df = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "5m", since=since, limit=120000)
    print(f"Loaded {len(df)} candles.")
    
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    
    # Macro trend proxy on 5m (800 periods = ~3 days)
    e800 = _ema(close, 800)
    
    # Volume anomaly on 5m
    v50 = _sma(vol, 50)
    
    # Bollinger Bands to detect micro-sweeps
    sma20 = _sma(close, 20)
    std20 = close.rolling(20).std()
    bb_lower = sma20 - 2.5 * std20 # 2.5 STD for extreme sweeps
    
    trades = []
    i = 805
    
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        v = float(vol.iloc[i])
        v_ma = float(v50.iloc[i]) if pd.notna(v50.iloc[i]) else 0
        b_low = float(bb_lower.iloc[i]) if pd.notna(bb_lower.iloc[i]) else 0
        e8 = float(e800.iloc[i]) if pd.notna(e800.iloc[i]) else 0
        
        # Trigger Conditions:
        # 1. Price is in a macro uptrend (C > EMA 800)
        # 2. Extreme Liquidity Sweep (Low pierces 2.5 STD lower band)
        # 3. Volume is explosive (Vol > 4.0 * V_MA) to indicate Smart Money stepping in
        # 4. Rejection (Close in the top 30% of the candle range)
        
        vol_mult = v / v_ma if v_ma > 0 else 0
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        
        if c > e8 and l < b_low and vol_mult > 4.0 and close_pct > 0.7:
            entry = c
            # FIXED SL AND TP
            sl = entry * (1 - 0.005) # 0.5% Stoploss
            tp = entry * (1 + 0.10)  # 10.0% Take Profit
            
            # Since SL is so tight, if the current candle's low is ALREADY below SL, we were stopped out in the same candle!
            if l <= sl:
                # Instant stopout (Wick swept too far after our entry criteria theoretically)
                # But realistically we enter on CLOSE of the 5m candle. So we only care about future candles.
                pass
                
            j = i + 1
            exit_idx = None
            result = None
            
            while j < len(df):
                hi = float(high.iloc[j])
                lo = float(low.iloc[j])
                
                # Check SL first (pessimistic execution)
                if lo <= sl: 
                    exit_idx, result = j, "LOSS"
                    break
                if hi >= tp: 
                    exit_idx, result = j, "WIN"
                    break
                j += 1
                
            if exit_idx is not None:
                trades.append(result)
                i = exit_idx # Skip to exit index to avoid overlapping trades
        i += 1
        
    wins = trades.count("WIN")
    losses = trades.count("LOSS")
    total = len(trades)
    wr = wins / total * 100 if total else 0
    net_r = (wins * 20.0) - (losses * 1.0) # RR = 20
    
    print("\n--- 5M SMC SNIPER (SL 0.5% / TP 10%) ---")
    print(f"Total Trades: {total}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Winrate: {wr:.2f}%")
    print(f"Net Profit (RR=20): {net_r:+.2f}R")

if __name__ == "__main__":
    test_5m()
