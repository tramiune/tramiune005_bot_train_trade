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

async def fetch_data():
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = 90 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv('XRP/USDT', '5m', since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + 300000 
        except:
            await asyncio.sleep(1)
    await exchange.close()
    return all_klines

async def run():
    print("Fetching 90 days XRP 5m...")
    xrp_data = await fetch_data()
    df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    print("Calculating Nada, RSI & Volume...")
    df['nada_low'] = calculate_causal_nadaraya_watson(df['close'], h=8, window=100, mult=1.5)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    
    tp_pct = 1.5; sl_pct = 3.0; maker_fee = 0.02 / 100
    rsi_limit = 40; vol_limit = 1.0
    trades = []
    
    print("Running Optimal Strategy...")
    i = 200
    while i < len(df) - 1:
        if df['low'].iloc[i] <= df['nada_low'].iloc[i] and df['close'].iloc[i] > df['nada_low'].iloc[i]:
            if df['rsi'].iloc[i] < rsi_limit and df['vol_ratio'].iloc[i] > vol_limit:
                
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
                        "month": df['datetime'].iloc[i].strftime('%Y-%m')
                    })
                    i = exit_idx
                else:
                    i += 1
                continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    print("\n=== MONTHLY BREAKDOWN (XRP 5M OPTIMAL) ===")
    
    for month in sorted(res_df['month'].unique()):
        m_df = res_df[res_df['month'] == month]
        wins = m_df['is_win'].sum()
        losses = len(m_df) - wins
        wr = (wins / len(m_df)) * 100 if len(m_df) > 0 else 0
        pnl = (wins * (tp_pct - maker_fee*2*100)) - (losses * (sl_pct + maker_fee*2*100))
        print(f"[{month}] Trades: {len(m_df)} | Wins: {wins} | Losses: {losses} | WinRate: {wr:.1f}% | NetPnL: +{pnl:.2f}%" if pnl > 0 else f"[{month}] Trades: {len(m_df)} | Wins: {wins} | Losses: {losses} | WinRate: {wr:.1f}% | NetPnL: {pnl:.2f}%")

asyncio.run(run())
