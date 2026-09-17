import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from server.main import _fetch_ohlcv_ccxt, _atr, _ema, _sma

def get_supertrend(df, period=10, multiplier=3.0):
    atr = _atr(df, period)
    hl2 = (df['high'] + df['low']) / 2
    basic_ub = hl2 + multiplier * atr
    basic_lb = hl2 - multiplier * atr
    final_ub = np.zeros(len(df))
    final_lb = np.zeros(len(df))
    supertrend = np.zeros(len(df))
    close = df['close'].values
    for i in range(period, len(df)):
        if basic_ub.iloc[i] < final_ub[i-1] or close[i-1] > final_ub[i-1]: final_ub[i] = basic_ub.iloc[i]
        else: final_ub[i] = final_ub[i-1]
        if basic_lb.iloc[i] > final_lb[i-1] or close[i-1] < final_lb[i-1]: final_lb[i] = basic_lb.iloc[i]
        else: final_lb[i] = final_lb[i-1]
        if supertrend[i-1] == 1 and close[i] < final_lb[i]: supertrend[i] = -1
        elif supertrend[i-1] == -1 and close[i] > final_ub[i]: supertrend[i] = 1
        elif supertrend[i-1] == 0: supertrend[i] = 1 if close[i] > final_ub[i] else -1
        else: supertrend[i] = supertrend[i-1]
    df['st'] = supertrend
    df['ub'] = final_ub
    df['lb'] = final_lb
    return df

def run_analysis():
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    df = _fetch_ohlcv_ccxt("binance", "AVAX/USDT", "1h", since=since, limit=100000)
    btc = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=100000)
    btc = btc[["timestamp", "close"]].rename(columns={"close": "btc_c"})
    
    df = pd.merge(df, btc, on="timestamp", how="left")
    df['e200'] = _ema(df['close'].astype(float), 200)
    df['btc_e200'] = _ema(df['btc_c'].astype(float), 200)
    df['v20'] = _sma(df['volume'].astype(float), 20)
    df['atr14'] = _atr(df, 14)
    
    df = get_supertrend(df, period=10, multiplier=3.0)
    
    trades = []
    
    i = 205
    while i < len(df) - 1:
        if df['st'].iloc[i-1] == -1 and df['st'].iloc[i] == 1 and df['close'].iloc[i] > df['e200'].iloc[i]:
            entry = float(df['close'].iloc[i])
            initial_risk = entry - float(df['lb'].iloc[i])
            
            # Record characteristics AT ENTRY
            vol_mult = float(df['volume'].iloc[i] / df['v20'].iloc[i]) if pd.notna(df['v20'].iloc[i]) and df['v20'].iloc[i] > 0 else 0
            btc_is_bullish = float(df['btc_c'].iloc[i]) > float(df['btc_e200'].iloc[i])
            dt = pd.to_datetime(df['timestamp'].iloc[i], utc=True)
            day_of_week = dt.dayofweek
            atr_pct = float(df['atr14'].iloc[i]) / entry * 100
            
            if initial_risk > 0:
                j = i + 1
                while j < len(df):
                    if df['st'].iloc[j] == -1:
                        exit_price = float(df['close'].iloc[j])
                        profit_R = (exit_price - entry) / initial_risk
                        result = "WIN" if profit_R > 0 else "LOSS"
                        trades.append({
                            "result": result,
                            "vol_mult": vol_mult,
                            "btc_bull": btc_is_bullish,
                            "day": day_of_week,
                            "atr_pct": atr_pct,
                            "R": profit_R
                        })
                        i = j
                        break
                    j += 1
        i += 1

    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    
    print("\n--- AVAX SUPERTREND LOSS ANALYSIS ---")
    print(f"Total Wins: {len(wins)}")
    print(f"Total Losses: {len(losses)}")
    
    # 1. Volume Analysis
    w_vol = np.mean([t['vol_mult'] for t in wins])
    l_vol = np.mean([t['vol_mult'] for t in losses])
    print(f"\nAvg Volume Multiplier at Entry -> Wins: {w_vol:.2f}x | Losses: {l_vol:.2f}x")
    
    # 2. BTC Macro Trend Analysis
    w_btc = sum([1 for t in wins if t['btc_bull']]) / len(wins) * 100
    l_btc = sum([1 for t in losses if t['btc_bull']]) / len(losses) * 100
    print(f"BTC was in Uptrend at Entry -> Wins: {w_btc:.1f}% | Losses: {l_btc:.1f}%")
    
    # 3. ATR Volatility Analysis
    w_atr = np.mean([t['atr_pct'] for t in wins])
    l_atr = np.mean([t['atr_pct'] for t in losses])
    print(f"Avg ATR% at Entry -> Wins: {w_atr:.2f}% | Losses: {l_atr:.2f}%")
    
    # 4. Day of Week Analysis (0=Mon, 6=Sun)
    print("\nDay of Week Distribution (Losses vs Wins):")
    for d, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        w_day = len([t for t in wins if t['day'] == d])
        l_day = len([t for t in losses if t['day'] == d])
        print(f"{name}: {w_day} Wins, {l_day} Losses -> Winrate: {w_day/(w_day+l_day)*100 if w_day+l_day>0 else 0:.1f}%")

if __name__ == "__main__":
    run_analysis()
