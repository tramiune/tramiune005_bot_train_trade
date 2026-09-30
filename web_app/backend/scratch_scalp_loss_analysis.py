import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

def calculate_vwap(df):
    q = df['volume'] * ((df['high'] + df['low'] + df['close']) / 3)
    return q.rolling(window=1440).sum() / df['volume'].rolling(window=1440).sum()

async def fetch_3_months(symbol):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ninety_days_ms = 90 * 24 * 60 * 60 * 1000
    since = now - ninety_days_ms
    all_klines = []
    
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, '1m', since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + 60000
        except:
            await asyncio.sleep(1)
    await exchange.close()
    return all_klines

async def run():
    print("Fetching data...")
    sol_data = await fetch_3_months('SOL/USDT')
    btc_data = await fetch_3_months('BTC/USDT')
    
    df = pd.DataFrame(sol_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    btc_df = btc_df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df = pd.merge(df, btc_df[['timestamp', 'close']], on='timestamp', how='inner', suffixes=('', '_btc'))
    
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['vwap'] = calculate_vwap(df)
    df['btc_ema200'] = df['close_btc'].ewm(span=200, adjust=False).mean()
    
    tp_pct = 1.5; sl_pct = 0.7
    trades = []
    
    print("Analyzing losses...")
    i = 1500
    while i < len(df) - 1:
        if df['close'].iloc[i] > df['vwap'].iloc[i]:
            if df['ema9'].iloc[i] > df['ema21'].iloc[i]:
                if df['low'].iloc[i] <= df['ema21'].iloc[i] and df['close'].iloc[i] > df['ema21'].iloc[i]:
                    vwap_dist = ((df['close'].iloc[i] - df["vwap"].iloc[i]) / df["vwap"].iloc[i]) * 100
                    hour = pd.to_datetime(df["timestamp"].iloc[i], unit='ms').hour
                    btc_bullish = df['close_btc'].iloc[i] > df['btc_ema200'].iloc[i]
                    
                    if vwap_dist > 0.8 and (12 <= hour <= 18) and btc_bullish:
                        entry_price = df['close'].iloc[i]
                        sl = entry_price * (1 - sl_pct/100)
                        tp = entry_price * (1 + tp_pct/100)
                        
                        is_win = False; exit_idx = i
                        for j in range(i+1, min(i+1440, len(df))):
                            if df['low'].iloc[j] <= sl:
                                is_win = False; exit_idx = j; break
                            elif df['high'].iloc[j] >= tp:
                                is_win = True; exit_idx = j; break
                                
                        if exit_idx > i:
                            ts = pd.to_datetime(df["timestamp"].iloc[i], unit='ms')
                            trades.append({
                                "is_win": is_win,
                                "hour": hour,
                                "dow": ts.dayofweek,
                                "volume": df['volume'].iloc[i]
                            })
                            i = exit_idx
                        else:
                            i += 1
                        continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    print("\n--- WIN/LOSS BY HOUR (UTC) ---")
    hour_stats = res_df.groupby('hour')['is_win'].agg(['count', 'sum'])
    hour_stats.columns = ['Total', 'Wins']
    hour_stats['Losses'] = hour_stats['Total'] - hour_stats['Wins']
    hour_stats['WinRate'] = (hour_stats['Wins'] / hour_stats['Total'] * 100).round(1)
    print(hour_stats)

    print("\n--- WIN/LOSS BY DAY OF WEEK (0=Mon, 6=Sun) ---")
    dow_stats = res_df.groupby('dow')['is_win'].agg(['count', 'sum'])
    dow_stats.columns = ['Total', 'Wins']
    dow_stats['Losses'] = dow_stats['Total'] - dow_stats['Wins']
    dow_stats['WinRate'] = (dow_stats['Wins'] / dow_stats['Total'] * 100).round(1)
    print(dow_stats)
    
asyncio.run(run())
