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

def _supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    hl2 = (df['high'] + df['low']) / 2
    atr = _atr(df, period)
    basic_ub = hl2 + (multiplier * atr)
    basic_lb = hl2 - (multiplier * atr)
    final_ub = pd.Series(index=df.index, dtype='float64')
    final_lb = pd.Series(index=df.index, dtype='float64')
    trend = pd.Series(index=df.index, dtype='float64')
    final_ub.iloc[0] = basic_ub.iloc[0]
    final_lb.iloc[0] = basic_lb.iloc[0]
    trend.iloc[0] = 1

    for i in range(1, len(df)):
        if pd.isna(basic_ub.iloc[i]):
            final_ub.iloc[i] = np.nan
            final_lb.iloc[i] = np.nan
            trend.iloc[i] = 1
            continue
        if np.isnan(final_ub.iloc[i-1]) or basic_ub.iloc[i] < final_ub.iloc[i-1] or df['close'].iloc[i-1] > final_ub.iloc[i-1]:
            final_ub.iloc[i] = basic_ub.iloc[i]
        else:
            final_ub.iloc[i] = final_ub.iloc[i-1]
        if np.isnan(final_lb.iloc[i-1]) or basic_lb.iloc[i] > final_lb.iloc[i-1] or df['close'].iloc[i-1] < final_lb.iloc[i-1]:
            final_lb.iloc[i] = basic_lb.iloc[i]
        else:
            final_lb.iloc[i] = final_lb.iloc[i-1]
        if trend.iloc[i-1] == 1 and df['close'].iloc[i] < final_lb.iloc[i]:
            trend.iloc[i] = -1
        elif trend.iloc[i-1] == -1 and df['close'].iloc[i] > final_ub.iloc[i]:
            trend.iloc[i] = 1
        else:
            trend.iloc[i] = trend.iloc[i-1]
    return trend

def fetch_data():
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
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
    return df

def run_grid_search():
    df = fetch_data()
    df["st_dir"] = _supertrend(df, 10, 3.0)
    df["atr14"] = _atr(df, 14)
    
    # Store all BULLISH breakouts (Retail buys, we will SHORT)
    setups = []
    i = 205
    while i < len(df) - 1:
        c = df["close"].iloc[i]
        st_dir = df["st_dir"].iloc[i]
        prev_st_dir = df["st_dir"].iloc[i-1]
        at = df["atr14"].iloc[i]
        
        # Bullish flip
        if prev_st_dir == -1 and st_dir == 1:
            setups.append({
                'idx': i,
                'entry': c,
                'atr': at
            })
        i += 1

    print(f"Found {len(setups)} Bullish Breakouts. We will SHORT all of them.")
    
    sl_multipliers = [1.0, 1.5, 2.0]
    rr_targets = [1.0, 1.5, 2.0, 3.0]
    
    results = []
    
    for sl_mult in sl_multipliers:
        for rr in rr_targets:
            wins = 0
            losses = 0
            
            for s in setups:
                entry = s['entry']
                
                # SHORT POSITION MATH
                sl = entry + sl_mult * s['atr']
                risk = sl - entry
                tp = entry - rr * risk
                
                j = s['idx'] + 1
                res = None
                while j < len(df):
                    hi = df["high"].iloc[j]
                    lo = df["low"].iloc[j]
                    
                    # For a SHORT, hitting high is a loss, hitting low is a win
                    if hi >= sl: 
                        res = "LOSS"
                        break
                    if lo <= tp:
                        res = "WIN"
                        break
                    j += 1
                    
                if res == "WIN": wins += 1
                elif res == "LOSS": losses += 1
                
            tot = wins + losses
            wr = wins / tot * 100 if tot else 0
            net_r = (wins * rr) - (losses * 1.0)
            results.append((sl_mult, rr, tot, wins, losses, wr, net_r))
            
    # Sort by Net R
    results.sort(key=lambda x: x[6], reverse=True)
    
    print("\n--- SUI FAKEOUT SHORT STRATEGY (Mean Reversion) ---")
    print(f"{'SL (ATR)':<10} | {'RR':<5} | {'Trades':<6} | {'Wins':<4} | {'Losses':<6} | {'WR %':<6} | {'Net R':<6}")
    print("-" * 65)
    for r in results:
        print(f"{r[0]:<10.1f} | {r[1]:<5.1f} | {r[2]:<6} | {r[3]:<4} | {r[4]:<6} | {r[5]:<6.1f} | {r[6]:<+6.1f}")

if __name__ == "__main__":
    run_grid_search()
