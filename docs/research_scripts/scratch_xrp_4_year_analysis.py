import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt
import sys

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

async def fetch_data(symbol, years=4):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = years * 365 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    
    count = 0
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, '5m', since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + 300000 
            count += 1
            if count % 20 == 0:
                print(f"[{symbol}] Fetched {len(all_klines)} candles...")
                sys.stdout.flush()
        except Exception:
            await asyncio.sleep(1)
    await exchange.close()
    return all_klines

async def run():
    print("Fetching 4-Year Data (Takes ~4 mins)...")
    xrp_data = await fetch_data('XRP/USDT', years=4)
    btc_data = await fetch_data('BTC/USDT', years=4)
    
    df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    btc_df = btc_df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df = pd.merge(df, btc_df[['timestamp', 'close']], on='timestamp', how='inner', suffixes=('', '_btc'))
    
    print("Calculating Nadaraya-Watson...")
    df['nada_low'] = calculate_causal_nadaraya_watson(df['close'], h=8, window=100, mult=1.5)
    
    print("Calculating other indicators...")
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    df['btc_ema200'] = df['close_btc'].ewm(span=200, adjust=False).mean()
    df['xrp_ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    tp_pct = 1.5; sl_pct = 3.0
    trades = []
    
    print("Extracting 1000+ trades for statistical analysis...")
    i = 500
    while i < len(df) - 1:
        if df['low'].iloc[i] <= df['nada_low'].iloc[i] and df['close'].iloc[i] > df['nada_low'].iloc[i]:
            if df['rsi'].iloc[i] < 40 and df['vol_ratio'].iloc[i] > 1.0:
                if df['close_btc'].iloc[i] > df['btc_ema200'].iloc[i]:
                    
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
                            "xrp_above_ema": (df['close'].iloc[i] > df['xrp_ema200'].iloc[i])
                        })
                        i = exit_idx
                    else:
                        i += 1
                    continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    wins = res_df[res_df['is_win'] == True]
    losses = res_df[res_df['is_win'] == False]
    
    print("\n" + "="*50)
    print(f"=== DEEP DIVE: 4 YEARS (WINS: {len(wins)} vs LOSSES: {len(losses)}) ===")
    print("="*50)
    
    print("\n[RSI ANALYSIS]")
    print(f"Avg RSI (Wins): {wins['rsi'].mean():.2f} | Avg RSI (Losses): {losses['rsi'].mean():.2f}")
    
    rsi_thresholds = [35, 30, 25, 20]
    for r in rsi_thresholds:
        w = len(wins[wins['rsi'] < r])
        l = len(losses[losses['rsi'] < r])
        wr = (w / (w+l)*100) if (w+l)>0 else 0
        print(f"If RSI < {r}: Wins={w}, Losses={l} (WinRate: {wr:.1f}%)")
        
    print("\n[VOLUME RATIO ANALYSIS]")
    print(f"Avg Vol_Ratio (Wins): {wins['vol_ratio'].mean():.2f} | Avg Vol_Ratio (Losses): {losses['vol_ratio'].mean():.2f}")
    vol_thresholds = [1.5, 2.0, 2.5, 3.0]
    for v in vol_thresholds:
        w = len(wins[wins['vol_ratio'] > v])
        l = len(losses[losses['vol_ratio'] > v])
        wr = (w / (w+l)*100) if (w+l)>0 else 0
        print(f"If Vol_Ratio > {v}: Wins={w}, Losses={l} (WinRate: {wr:.1f}%)")
        
    print("\n[MACRO XRP TREND ANALYSIS]")
    w_above = len(wins[wins['xrp_above_ema'] == True])
    l_above = len(losses[losses['xrp_above_ema'] == True])
    wr_above = (w_above / (w_above+l_above)*100) if (w_above+l_above)>0 else 0
    print(f"If XRP > EMA200 (Uptrend): Wins={w_above}, Losses={l_above} (WinRate: {wr_above:.1f}%)")
    
    w_below = len(wins[wins['xrp_above_ema'] == False])
    l_below = len(losses[losses['xrp_above_ema'] == False])
    wr_below = (w_below / (w_below+l_below)*100) if (w_below+l_below)>0 else 0
    print(f"If XRP < EMA200 (Downtrend): Wins={w_below}, Losses={l_below} (WinRate: {wr_below:.1f}%)")

asyncio.run(run())
