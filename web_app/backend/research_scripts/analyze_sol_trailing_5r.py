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

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()

def run_analysis():
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    since = exchange.parse8601((datetime.now(timezone.utc) - timedelta(days=1460)).isoformat())
    
    all_sol = []
    sol_since = since
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv("SOL/USDT", '1h', sol_since, 1000)
            if not len(ohlcv): break
            all_sol += ohlcv
            sol_since = ohlcv[-1][0] + 3600000 
            if len(ohlcv) < 1000: break
        except: break
    
    all_btc = []
    btc_since = since
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv("BTC/USDT", '1h', btc_since, 1000)
            if not len(ohlcv): break
            all_btc += ohlcv
            btc_since = ohlcv[-1][0] + 3600000 
            if len(ohlcv) < 1000: break
        except: break
        
    sol = pd.DataFrame(all_sol, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    sol['timestamp'] = pd.to_datetime(sol['timestamp'], unit='ms', utc=True)
    sol.drop_duplicates(subset='timestamp', inplace=True)
    
    btc = pd.DataFrame(all_btc, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    btc['timestamp'] = pd.to_datetime(btc['timestamp'], unit='ms', utc=True)
    btc.drop_duplicates(subset='timestamp', inplace=True)
    btc = btc[["timestamp", "close"]].rename(columns={"close": "btc_close"})
    
    df = pd.merge(sol, btc, on="timestamp", how="left")
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    df["e200"] = _ema(df["close"].astype(float), 200)
    df["e20"] = _ema(df["close"].astype(float), 20)
    df["atr14"] = _atr(df, 14)
    df["v20"] = _sma(df["volume"].astype(float), 20)
    df["btc_e200"] = _ema(df["btc_close"].astype(float), 200)
    
    winning_trades_retrace = []
    i = 205
    last_bullish_cross_idx = 0
    atr_mult = 1.8
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
        
        if prev_e20 <= prev_e200 and e20_val > e200_val:
            last_bullish_cross_idx = i
            
        close_pct = (c - l) / (h - l) if (h - l) > 0 else 0
        dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
        
        is_uptrend = e20_val > e200_val
        candles_since_cross = i - last_bullish_cross_idx
        is_proper_speed = 20 <= candles_since_cross < 150
        is_touching = l <= e200_val and c > e200_val
        is_strong_rejection = close_pct > 0.6
        has_volume = (v / v_ma) > 1.2 if v_ma > 0 else False
        btc_bullish = btc_c > btc_e200_val
        is_midweek = dt.dayofweek in [1, 2, 3] 
        
        if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and has_volume and btc_bullish and is_midweek:
            entry = c
            sl = entry - atr_mult * at
            risk = entry - sl
            
            if risk > 0:
                tp = entry + rr_target * risk
                j = i + 1
                
                reached_5r = False
                lowest_r_after_5r = 999.0
                exit_idx = None
                
                while j < len(df):
                    hi = float(df["high"].iloc[j])
                    lo = float(df["low"].iloc[j])
                    
                    if reached_5r:
                        current_low_r = (lo - entry) / risk
                        if current_low_r < lowest_r_after_5r:
                            lowest_r_after_5r = current_low_r
                            
                    if not reached_5r and hi >= (entry + 5.0 * risk):
                        reached_5r = True
                        
                    if lo <= sl: 
                        exit_idx = j
                        result = "LOSS"
                        break
                    if hi >= tp: 
                        exit_idx = j
                        result = "WIN"
                        break
                    j += 1
                    
                if exit_idx is not None:
                    if result == "WIN":
                        winning_trades_retrace.append({
                            'date': dt.strftime('%Y-%m-%d'),
                            'lowest_r_after_5r': lowest_r_after_5r if reached_5r else "Never hit 5R"
                        })
                    i = exit_idx
                    continue
        i += 1
        
    print(f"\n--- WINNING TRADES RETRACE ANALYSIS (Reach +5R, trail to +2R) ---")
    killed_wins = 0
    for idx, win in enumerate(winning_trades_retrace):
        lowest = win['lowest_r_after_5r']
        if isinstance(lowest, float):
            status = "KILLED BY +2R TRAIL" if lowest <= 2.0 else "SURVIVED"
            if lowest <= 2.0: killed_wins += 1
            print(f"Win {idx+1} ({win['date']}): Dropped to {lowest:+.2f} R after hitting 5R. -> {status}")
            
    print(f"\nTotal Winning Trades: {len(winning_trades_retrace)}")
    print(f"Number of 15R Wins KILLED: {killed_wins}")

if __name__ == "__main__":
    run_analysis()
