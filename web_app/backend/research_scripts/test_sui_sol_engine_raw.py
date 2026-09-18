import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def run_analysis():
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    # SUI launched mid 2023, so 700 days is enough
    since = exchange.parse8601((datetime.now(timezone.utc) - timedelta(days=700)).isoformat())
    
    all_data = []
    print("Fetching SUI/USDT data...")
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv("SUI/USDT", '1h', since, 1000)
            if not len(ohlcv): break
            all_data += ohlcv
            since = ohlcv[-1][0] + 3600000 
            if len(ohlcv) < 1000: break
        except Exception as e:
            break
            
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.drop_duplicates(subset='timestamp', inplace=True)
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    df["e200"] = _ema(df["close"].astype(float), 200)
    df["e20"] = _ema(df["close"].astype(float), 20)
    df["atr14"] = _atr(df, 14)
    
    trades = []
    i = 205
    last_bullish_cross_idx = 0
    atr_mult = 1.8
    rr_target = 15.0
    
    while i < len(df) - 1:
        c = float(df["close"].iloc[i])
        h = float(df["high"].iloc[i])
        l = float(df["low"].iloc[i])
        
        e200_val = float(df["e200"].iloc[i]) if pd.notna(df["e200"].iloc[i]) else 0
        e20_val = float(df["e20"].iloc[i]) if pd.notna(df["e20"].iloc[i]) else 0
        prev_e20 = float(df["e20"].iloc[i-1]) if pd.notna(df["e20"].iloc[i-1]) else 0
        prev_e200 = float(df["e200"].iloc[i-1]) if pd.notna(df["e200"].iloc[i-1]) else 0
        at = float(df["atr14"].iloc[i]) if pd.notna(df["atr14"].iloc[i]) else 0
        
        if prev_e20 <= prev_e200 and e20_val > e200_val:
            last_bullish_cross_idx = i
            
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        
        # RAW BASELINE FILTERS (NO OPTIMIZATIONS)
        is_uptrend = e20_val > e200_val
        candles_since_cross = i - last_bullish_cross_idx
        is_proper_speed = 20 <= candles_since_cross < 150
        is_touching = l <= e200_val and c > e200_val
        is_strong_rejection = close_pct > 0.6  # Standard Pinbar logic
        
        if is_uptrend and is_proper_speed and is_touching and is_strong_rejection:
            entry = c
            sl = entry - atr_mult * at
            risk = entry - sl
            
            if risk > 0:
                tp = entry + rr_target * risk
                j = i + 1
                exit_idx = None
                result = None
                
                while j < len(df):
                    hi = float(df["high"].iloc[j])
                    lo = float(df["low"].iloc[j])
                    if lo <= sl: exit_idx, result = j, "LOSS"; break
                    if hi >= tp: exit_idx, result = j, "WIN"; break
                    j += 1
                    
                if exit_idx is not None:
                    dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
                    trades.append({
                        'result': result,
                        'date': dt.strftime('%Y-%m-%d %H:%M')
                    })
                    i = exit_idx
                    continue
        i += 1
        
    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    total = len(trades)
    
    print("\n" + "="*50)
    print(" SUI - RAW SOL ENGINE BASELINE (EMA200 Retest)")
    print(" RR 15.0, StopLoss 1.8 ATR. NO FILTERS.")
    print("="*50)
    print(f"Total Trades : {total}")
    print(f"Wins         : {len(wins)}")
    print(f"Losses       : {len(losses)}")
    wr = len(wins) / total * 100 if total > 0 else 0
    print(f"Winrate      : {wr:.1f}%")
    net_r = (len(wins) * 15.0) - (len(losses) * 1.0)
    print(f"Net Profit   : {net_r:+.1f} R")
    print("="*50)

if __name__ == "__main__":
    run_analysis()
