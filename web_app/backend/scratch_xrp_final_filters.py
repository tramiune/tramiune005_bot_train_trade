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
    
    # Return multiple bands
    return df['smoothed'] - (1.5 * df['mae']), df['smoothed'] - (2.0 * df['mae']), df['smoothed'] - (2.5 * df['mae'])

async def fetch_data(symbol, years=1):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = years * 365 * 24 * 60 * 60 * 1000
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

def get_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

async def run():
    print("Fetching 1-Year Data for advanced filter testing...")
    xrp_data = await fetch_data('XRP/USDT', years=1)
    btc_data = await fetch_data('BTC/USDT', years=1)
    
    df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    btc_df = btc_df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df = pd.merge(df, btc_df[['timestamp', 'close', 'high', 'low']], on='timestamp', how='inner', suffixes=('', '_btc'))
    
    nada_15, nada_20, nada_25 = calculate_causal_nadaraya_watson(df['close'])
    df['nada_15'] = nada_15
    df['nada_20'] = nada_20
    df['nada_25'] = nada_25
    
    df['rsi'] = get_rsi(df['close'])
    df['btc_rsi'] = get_rsi(df['close_btc'])
    
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    df['btc_ema200'] = df['close_btc'].ewm(span=200, adjust=False).mean()
    
    df['atr'] = get_atr(df['high'], df['low'], df['close'])
    df['atr_ma'] = df['atr'].rolling(window=100).mean()
    df['atr_ratio'] = df['atr'] / df['atr_ma']
    
    tp_pct = 1.5; sl_pct = 3.0
    trades = []
    
    i = 500
    while i < len(df) - 1:
        # Base trigger on 1.5 band
        if df['low'].iloc[i] <= df['nada_15'].iloc[i] and df['close'].iloc[i] > df['nada_15'].iloc[i]:
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
                            "btc_rsi": df['btc_rsi'].iloc[i],
                            "atr_ratio": df['atr_ratio'].iloc[i],
                            "touched_nada_20": df['low'].iloc[i] <= df['nada_20'].iloc[i],
                            "touched_nada_25": df['low'].iloc[i] <= df['nada_25'].iloc[i]
                        })
                        i = exit_idx
                    else:
                        i += 1
                    continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    wins = res_df[res_df['is_win'] == True]
    losses = res_df[res_df['is_win'] == False]
    
    print("\n=== ADVANCED FILTER TEST (1 YEAR) ===")
    print(f"Base Trades: {len(res_df)} | Wins: {len(wins)} | Losses: {len(losses)} | WinRate: {len(wins)/len(res_df)*100:.1f}%")
    
    print("\n1. NADA MULTIPLIER FILTER (Wait for deeper drop)")
    w = len(wins[wins['touched_nada_20'] == True]); l = len(losses[losses['touched_nada_20'] == True])
    wr = w/(w+l)*100 if (w+l)>0 else 0
    print(f"Require crossing NADA 2.0 -> Trades: {w+l} | Wins: {w} | Losses: {l} | WinRate: {wr:.1f}%")
    
    w = len(wins[wins['touched_nada_25'] == True]); l = len(losses[losses['touched_nada_25'] == True])
    wr = w/(w+l)*100 if (w+l)>0 else 0
    print(f"Require crossing NADA 2.5 -> Trades: {w+l} | Wins: {w} | Losses: {l} | WinRate: {wr:.1f}%")
    
    print("\n2. BTC RSI FILTER (Is BTC crashing too?)")
    print(f"Avg BTC RSI (Wins): {wins['btc_rsi'].mean():.1f} | Avg BTC RSI (Losses): {losses['btc_rsi'].mean():.1f}")
    w = len(wins[wins['btc_rsi'] > 30]); l = len(losses[losses['btc_rsi'] > 30])
    wr = w/(w+l)*100 if (w+l)>0 else 0
    print(f"Require BTC RSI > 30 -> Trades: {w+l} | Wins: {w} | Losses: {l} | WinRate: {wr:.1f}%")
    
    print("\n3. ATR VOLATILITY FILTER (Avoid market chaos)")
    print(f"Avg ATR Ratio (Wins): {wins['atr_ratio'].mean():.2f} | Avg ATR Ratio (Losses): {losses['atr_ratio'].mean():.2f}")
    w = len(wins[wins['atr_ratio'] < 2.0]); l = len(losses[losses['atr_ratio'] < 2.0])
    wr = w/(w+l)*100 if (w+l)>0 else 0
    print(f"Require ATR Ratio < 2.0 (Normal vol) -> Trades: {w+l} | Wins: {w} | Losses: {l} | WinRate: {wr:.1f}%")

asyncio.run(run())
