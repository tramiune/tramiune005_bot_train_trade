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

def fetch_data(symbol, days=1460):
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    since = exchange.parse8601((datetime.now(timezone.utc) - timedelta(days=days)).isoformat())
    all_data = []
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', since, 1000)
            if not len(ohlcv): break
            all_data += ohlcv
            since = ohlcv[-1][0] + 3600000 
            if len(ohlcv) < 1000: break
        except: break
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.drop_duplicates(subset='timestamp', inplace=True)
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def run_analysis():
    print("Fetching data...")
    df = fetch_data("DOGE/USDT")
    btc_df = fetch_data("BTC/USDT")
    btc_df = btc_df[["timestamp", "close"]].rename(columns={"close": "btc_close"})
    
    df = pd.merge(df, btc_df, on="timestamp", how="left")
    df.dropna(subset=["btc_close"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    df["e200"] = _ema(df["close"].astype(float), 200)
    df["e20"] = _ema(df["close"].astype(float), 20)
    df["atr14"] = _atr(df, 14)
    df["btc_e200"] = _ema(df["btc_close"].astype(float), 200)
    
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
        btc_c = float(df["btc_close"].iloc[i]) if pd.notna(df["btc_close"].iloc[i]) else 0
        btc_e200_val = float(df["btc_e200"].iloc[i]) if pd.notna(df["btc_e200"].iloc[i]) else 0
        
        if prev_e20 <= prev_e200 and e20_val > e200_val:
            last_bullish_cross_idx = i
            
        candle_range = h - l
        close_pct = (c - l) / candle_range if candle_range > 0 else 0
        candle_size_pct = (candle_range / c) * 100
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        is_uptrend = e20_val > e200_val
        candles_since_cross = i - last_bullish_cross_idx
        is_proper_speed = 20 <= candles_since_cross < 150
        is_touching = l <= e200_val and c > e200_val
        
        # BASELINE FILTERS ALREADY PROVEN
        is_strong_rejection = close_pct > 0.6
        is_proper_session = 8 <= dt.hour <= 18
        is_proper_size = candle_size_pct < 2.5
        
        if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and is_proper_session and is_proper_size:
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
                    dist_to_e200 = ((c - e200_val) / e200_val) * 100
                    trades.append({
                        'result': result,
                        'day': dt.dayofweek,
                        'dist': dist_to_e200,
                        'btc_bullish': btc_c > btc_e200_val
                    })
                    i = exit_idx
                    continue
        i += 1
        
    print(f"\n--- BASELINE (Currently 57 Trades) ---")
    w = len([t for t in trades if t['result'] == 'WIN'])
    l = len([t for t in trades if t['result'] == 'LOSS'])
    print(f"Total: {len(trades)} | Wins: {w} | Losses: {l} | WR: {w/len(trades)*100:.1f}% | Net: {w*15.0 - l} R")
    
    print(f"\n--- FILTER A: No Trading on Friday/Saturday (day 4, 5) ---")
    f_a = [t for t in trades if t['day'] not in [4, 5]]
    w_a = len([t for t in f_a if t['result'] == 'WIN'])
    l_a = len([t for t in f_a if t['result'] == 'LOSS'])
    print(f"Total: {len(f_a)} | Wins: {w_a} | Losses: {l_a} | WR: {w_a/len(f_a)*100:.1f}% | Net: {w_a*15.0 - l_a} R")

    print(f"\n--- FILTER B: Perfect Touch (Distance to EMA 200 < 1.0%) ---")
    f_b = [t for t in trades if t['dist'] < 1.0]
    w_b = len([t for t in f_b if t['result'] == 'WIN'])
    l_b = len([t for t in f_b if t['result'] == 'LOSS'])
    print(f"Total: {len(f_b)} | Wins: {w_b} | Losses: {l_b} | WR: {w_b/len(f_b)*100:.1f}% | Net: {w_b*15.0 - l_b} R")
    
    print(f"\n--- FILTER C: BTC Macro Trend (BTC > EMA 200) ---")
    f_c = [t for t in trades if t['btc_bullish']]
    w_c = len([t for t in f_c if t['result'] == 'WIN'])
    l_c = len([t for t in f_c if t['result'] == 'LOSS'])
    print(f"Total: {len(f_c)} | Wins: {w_c} | Losses: {l_c} | WR: {w_c/len(f_c)*100:.1f}% | Net: {w_c*15.0 - l_c} R")
    
    print(f"\n--- COMBINED FILTERS (A + B + C) ---")
    f_all = [t for t in trades if t['day'] not in [4, 5] and t['dist'] < 1.0 and t['btc_bullish']]
    w_all = len([t for t in f_all if t['result'] == 'WIN'])
    l_all = len([t for t in f_all if t['result'] == 'LOSS'])
    print(f"Total: {len(f_all)} | Wins: {w_all} | Losses: {l_all} | WR: {w_all/len(f_all)*100:.1f}% | Net: {w_all*15.0 - l_all} R")

if __name__ == "__main__":
    run_analysis()
