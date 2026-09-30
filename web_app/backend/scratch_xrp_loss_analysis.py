import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

def calculate_causal_nadaraya_watson(close, h=8, window=100, mult=1.5):
    n = len(close)
    smoothed = np.zeros(n)
    smoothed[:] = np.nan
    i_arr = np.arange(window)
    weights = np.exp(-(i_arr**2) / (2 * h**2))
    sum_weights = np.sum(weights)
    close_vals = close.values
    for t in range(window, n):
        past_closes = close_vals[t-window+1 : t+1][::-1] 
        smoothed[t] = np.sum(past_closes * weights) / sum_weights
    df = pd.DataFrame({'close': close, 'smoothed': smoothed})
    df['mae'] = (df['close'] - df['smoothed']).abs().rolling(window=window).mean()
    df['lower'] = df['smoothed'] - (mult * df['mae'])
    return df['lower']

async def fetch_data(symbol):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = 365 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, '5m', since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + 300000 
        except:
            await asyncio.sleep(0.5)
    await exchange.close()
    return all_klines

async def run():
    xrp_data = await fetch_data('XRP/USDT')
    btc_data = await fetch_data('BTC/USDT')
    
    df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    btc_df = btc_df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df = pd.merge(df, btc_df[['timestamp', 'close']], on='timestamp', how='inner', suffixes=('', '_btc'))
    
    df['nada_low'] = calculate_causal_nadaraya_watson(df['close'], h=8, window=100, mult=1.5)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    df['btc_ema200'] = df['close_btc'].ewm(span=200, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['dist_ema'] = (df['close'] - df['ema200']) / df['ema200'] * 100
    
    tp_pct = 1.5; sl_pct = 3.0
    rsi_limit = 40; vol_limit = 1.0
    trades = []
    
    i = 500
    while i < len(df) - 1:
        if df['low'].iloc[i] <= df['nada_low'].iloc[i] and df['close'].iloc[i] > df['nada_low'].iloc[i]:
            if df['rsi'].iloc[i] < rsi_limit and df['vol_ratio'].iloc[i] > vol_limit:
                if df['close_btc'].iloc[i] > df['btc_ema200'].iloc[i]:
                    dt = df['datetime'].iloc[i]
                    if dt.dayofweek != 2 and dt.hour not in [4, 8, 9, 20]:
                        
                        entry_price = df['close'].iloc[i]
                        sl = entry_price * (1 - sl_pct/100)
                        tp = entry_price * (1 + tp_pct/100)
                        
                        is_win = False; exit_idx = i
                        for j in range(i+1, min(i+288, len(df))):
                            if df['low'].iloc[j] <= sl:
                                is_win = False; exit_idx = j; break
                            elif df['high'].iloc[j] >= tp:
                                is_win = True; exit_idx = j; break
                                
                        if exit_idx > i:
                            trades.append({
                                "is_win": is_win, 
                                "rsi": df['rsi'].iloc[i],
                                "vol_ratio": df['vol_ratio'].iloc[i],
                                "dist_ema": df['dist_ema'].iloc[i],
                                "hour": dt.hour,
                                "day": dt.dayofweek
                            })
                            i = exit_idx
                        else:
                            i += 1
                        continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    wins = res_df[res_df['is_win'] == True]
    losses = res_df[res_df['is_win'] == False]
    
    print("\n=== DEEP DIVE: WINS vs LOSSES ===")
    print(f"Number of Wins: {len(wins)} | Number of Losses: {len(losses)}")
    print("\n[RSI ANALYSIS]")
    print(f"Avg RSI (Wins): {wins['rsi'].mean():.2f} | Avg RSI (Losses): {losses['rsi'].mean():.2f}")
    print(f"RSI < 25 -> Wins: {len(wins[wins['rsi'] < 25])}, Losses: {len(losses[losses['rsi'] < 25])} (WinRate: {len(wins[wins['rsi'] < 25]) / (len(wins[wins['rsi'] < 25]) + len(losses[losses['rsi'] < 25]) + 0.0001) * 100:.1f}%)")
    print(f"RSI > 25 -> Wins: {len(wins[wins['rsi'] >= 25])}, Losses: {len(losses[losses['rsi'] >= 25])} (WinRate: {len(wins[wins['rsi'] >= 25]) / (len(wins[wins['rsi'] >= 25]) + len(losses[losses['rsi'] >= 25]) + 0.0001) * 100:.1f}%)")
    
    print("\n[VOLUME RATIO ANALYSIS]")
    print(f"Avg Vol_Ratio (Wins): {wins['vol_ratio'].mean():.2f} | Avg Vol_Ratio (Losses): {losses['vol_ratio'].mean():.2f}")
    print(f"Vol > 3.0 -> Wins: {len(wins[wins['vol_ratio'] > 3.0])}, Losses: {len(losses[losses['vol_ratio'] > 3.0])} (WinRate: {len(wins[wins['vol_ratio'] > 3.0]) / (len(wins[wins['vol_ratio'] > 3.0]) + len(losses[losses['vol_ratio'] > 3.0]) + 0.0001) * 100:.1f}%)")
    print(f"Vol < 3.0 -> Wins: {len(wins[wins['vol_ratio'] <= 3.0])}, Losses: {len(losses[losses['vol_ratio'] <= 3.0])} (WinRate: {len(wins[wins['vol_ratio'] <= 3.0]) / (len(wins[wins['vol_ratio'] <= 3.0]) + len(losses[losses['vol_ratio'] <= 3.0]) + 0.0001) * 100:.1f}%)")
    
    print("\n[DISTANCE TO EMA200 ANALYSIS]")
    print(f"Avg Dist (Wins): {wins['dist_ema'].mean():.2f}% | Avg Dist (Losses): {losses['dist_ema'].mean():.2f}%")
    print(f"Dist < -3% -> Wins: {len(wins[wins['dist_ema'] < -3.0])}, Losses: {len(losses[losses['dist_ema'] < -3.0])} (WinRate: {len(wins[wins['dist_ema'] < -3.0]) / (len(wins[wins['dist_ema'] < -3.0]) + len(losses[losses['dist_ema'] < -3.0]) + 0.0001) * 100:.1f}%)")
    print(f"Dist > -3% -> Wins: {len(wins[wins['dist_ema'] >= -3.0])}, Losses: {len(losses[losses['dist_ema'] >= -3.0])} (WinRate: {len(wins[wins['dist_ema'] >= -3.0]) / (len(wins[wins['dist_ema'] >= -3.0]) + len(losses[losses['dist_ema'] >= -3.0]) + 0.0001) * 100:.1f}%)")
    
    print("\n[REMAINING TOXIC HOURS ANALYSIS]")
    toxic_hours = []
    for h in range(24):
        if h in [4, 8, 9, 20]: continue
        hwins = len(wins[wins['hour'] == h])
        hlosses = len(losses[losses['hour'] == h])
        total = hwins + hlosses
        if total > 0 and (hwins / total) < 0.6:
            toxic_hours.append(f"Hour {h:02d}: Wins {hwins}, Losses {hlosses} (WinRate: {hwins/total*100:.1f}%)")
    for msg in toxic_hours: print(msg)

asyncio.run(run())
