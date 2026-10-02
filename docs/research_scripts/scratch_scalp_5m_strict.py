import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

def calculate_vwap(df):
    q = df['volume'] * ((df['high'] + df['low'] + df['close']) / 3)
    return q.rolling(window=288).sum() / df['volume'].rolling(window=288).sum()

def calculate_adx(df, period=14):
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff(-1).abs()
    
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx, atr

async def fetch_data():
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ninety_days_ms = 90 * 24 * 60 * 60 * 1000
    since = now - ninety_days_ms
    
    all_klines = []
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv('SOL/USDT', '5m', since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + (5 * 60000)
        except Exception:
            await asyncio.sleep(1)
    await exchange.close()
    return all_klines

async def run():
    print("Fetching 90 days of 5m data for strict testing...")
    data = await fetch_data()
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    adx, atr = calculate_adx(df, 14)
    df['adx'] = adx
    df['atr'] = atr
    
    maker_fee = 0.02 / 100
    results = []
    
    # Test Grids for 5m (Wider TP/SL)
    for tp_pct in [2.0, 3.0, 4.0]:
        for sl_pct in [1.0, 1.5, 2.0]:
            wins = 0
            losses = 0
            i = 300
            while i < len(df) - 1:
                # STRICT CONDITIONS:
                # 1. Macro Trend UP (Close > EMA200)
                # 2. Strong Trend (ADX > 25)
                # 3. Pullback Reversal (Previous close < EMA21, Current close > EMA21) -> Bullish engulfing/cross
                
                if df['close'].iloc[i] > df['ema200'].iloc[i] and df['adx'].iloc[i] > 25:
                    if df['close'].iloc[i-1] < df['ema21'].iloc[i-1] and df['close'].iloc[i] > df['ema21'].iloc[i]:
                        
                        entry_price = df['close'].iloc[i]
                        sl = entry_price * (1 - sl_pct/100)
                        tp = entry_price * (1 + tp_pct/100)
                        
                        is_win = False
                        exit_idx = i
                        for j in range(i+1, min(i+288, len(df))): # 1 day hold max
                            if df['low'].iloc[j] <= sl:
                                is_win = False
                                exit_idx = j
                                break
                            elif df['high'].iloc[j] >= tp:
                                is_win = True
                                exit_idx = j
                                break
                                
                        if exit_idx > i:
                            if is_win: wins += 1
                            else: losses += 1
                            i = exit_idx
                        else:
                            i += 1
                        continue
                i += 1
                
            total = wins + losses
            wr = (wins / total * 100) if total > 0 else 0
            limit_pnl = (wins * (tp_pct - maker_fee*2*100)) - (losses * (sl_pct + maker_fee*2*100))
            
            results.append({
                "TP": tp_pct,
                "SL": sl_pct,
                "Trades": total,
                "WinRate": wr,
                "NetPnL": limit_pnl
            })
            
    res_df = pd.DataFrame(results).sort_values(by="NetPnL", ascending=False)
    print("\n=== STRICT 5M STRATEGY RESULTS (SOL/USDT) ===")
    print(res_df.to_string(index=False))

asyncio.run(run())
