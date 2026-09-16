import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def _rsi(s, n=14):
    delta = s.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def test_bbands(df):
    # Mean reversion at lower bollinger band in uptrend
    close = df['close']
    sma20 = _sma(close, 20)
    std = close.rolling(20).std()
    lower_band = sma20 - 2 * std
    ema200 = _ema(close, 200)
    atr = _atr(df, 14)
    
    trades = []
    i = 205
    while i < len(df) - 1:
        c = float(close.iloc[i])
        e = float(ema200.iloc[i])
        lb = float(lower_band.iloc[i])
        at = float(atr.iloc[i]) if pd.notna(atr.iloc[i]) else 0
        
        # Uptrend + Price hits lower band
        if c > e and c <= lb and at > 0:
            entry = c
            sl = entry - 1.5 * at
            risk = entry - sl
            tp = entry + 2.0 * risk
            
            j = i + 1
            res = None
            while j < len(df):
                hi = float(df['high'].iloc[j])
                lo = float(df['low'].iloc[j])
                if lo <= sl: res = "LOSS"; break
                if hi >= tp: res = "WIN"; break
                j += 1
            if res:
                trades.append(res)
                i = j
        i += 1
    w = trades.count("WIN")
    return len(trades), (w/len(trades)*100 if trades else 0), "Bollinger Bands Mean Reversion"

def test_rsi_pullback(df):
    close = df['close']
    sma50 = _sma(close, 50)
    rsi = _rsi(close, 14)
    atr = _atr(df, 14)
    
    trades = []
    i = 55
    while i < len(df) - 1:
        c = float(close.iloc[i])
        s50 = float(sma50.iloc[i])
        r = float(rsi.iloc[i]) if pd.notna(rsi.iloc[i]) else 50
        at = float(atr.iloc[i]) if pd.notna(atr.iloc[i]) else 0
        
        # Strong uptrend + RSI drops below 40 (dip buying)
        if c > s50 and r < 40 and at > 0:
            entry = c
            sl = entry - 2 * at
            risk = entry - sl
            tp = entry + 2.0 * risk
            
            j = i + 1
            res = None
            while j < len(df):
                hi = float(df['high'].iloc[j])
                lo = float(df['low'].iloc[j])
                if lo <= sl: res = "LOSS"; break
                if hi >= tp: res = "WIN"; break
                j += 1
            if res:
                trades.append(res)
                i = j
        i += 1
    w = trades.count("WIN")
    return len(trades), (w/len(trades)*100 if trades else 0), "RSI Pullback in Uptrend"

def test_daily_breakout(df):
    close = df['close']
    high = df['high']
    highest_20 = high.rolling(20).max().shift(1)
    ema50 = _ema(close, 50)
    atr = _atr(df, 14)
    
    trades = []
    i = 55
    while i < len(df) - 1:
        c = float(close.iloc[i])
        h = float(high.iloc[i])
        e50 = float(ema50.iloc[i])
        h20 = float(highest_20.iloc[i]) if pd.notna(highest_20.iloc[i]) else 999999
        at = float(atr.iloc[i]) if pd.notna(atr.iloc[i]) else 0
        
        # Breakout above 20-day high in uptrend
        if c > e50 and c > h20 and at > 0:
            entry = c
            sl = entry - 1.5 * at
            risk = entry - sl
            tp = entry + 2.0 * risk
            
            j = i + 1
            res = None
            while j < len(df):
                hi = float(df['high'].iloc[j])
                lo = float(df['low'].iloc[j])
                if lo <= sl: res = "LOSS"; break
                if hi >= tp: res = "WIN"; break
                j += 1
            if res:
                trades.append(res)
                i = j
        i += 1
    w = trades.count("WIN")
    return len(trades), (w/len(trades)*100 if trades else 0), "Donchian Breakout (20-day high)"

def main():
    print("Searching for the Holy Grail: RR=2.0, Winrate >= 60%...")
    # Test across multiple timeframes for 4 years (1460 days)
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    
    results = []
    
    for tf in ["1d", "4h", "1h"]:
        print(f"Fetching {tf} data...")
        df = _fetch_ohlcv_ccxt("binance", "BTC/USDT", tf, since=since, limit=50000)
        print(f"Loaded {len(df)} candles for {tf}.")
        
        tests = [test_bbands, test_rsi_pullback, test_daily_breakout]
        for t in tests:
            tot, wr, name = t(df)
            if tot > 10:
                results.append((tf, name, tot, wr))
                print(f"[{tf}] {name}: Trades={tot}, WR={wr:.2f}%")
                
    print("\n--- FINAL RESULTS (Searching for WR >= 60%) ---")
    found = False
    for tf, name, tot, wr in results:
        if wr >= 60:
            print(f"✅ FOUND! [{tf}] {name} -> Trades: {tot}, Winrate: {wr:.2f}% (RR=2.0)")
            found = True
            
    if not found:
        print("❌ NO STRATEGY REACHED 60% WINRATE AT RR=2.0.")

if __name__ == "__main__":
    main()
