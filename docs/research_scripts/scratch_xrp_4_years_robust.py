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
        except Exception as e:
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
    print(f"Total synchronized 5m candles: {len(df)}")
    
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
    
    tp_pct = 1.5; sl_pct = 3.0; maker_fee = 0.02 / 100
    trades = []
    
    print("Simulating 4 years of ROBUST trades...")
    i = 500
    while i < len(df) - 1:
        if df['low'].iloc[i] <= df['nada_low'].iloc[i] and df['close'].iloc[i] > df['nada_low'].iloc[i]:
            if df['rsi'].iloc[i] < 40 and df['vol_ratio'].iloc[i] > 1.0:
                if df['close_btc'].iloc[i] > df['btc_ema200'].iloc[i]:
                    
                    # REMOVED TIME FILTERS COMPLETELY!
                    
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
                        dt = df['datetime'].iloc[i]
                        trades.append({
                            "is_win": is_win, 
                            "year": dt.year,
                            "month": dt.strftime('%Y-%m')
                        })
                        i = exit_idx
                    else:
                        i += 1
                    continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    
    print("\n" + "="*50)
    print("=== 4-YEAR ROBUST BACKTEST RESULTS (NO TIME FILTERS) ===")
    print("="*50)
    
    if len(res_df) == 0:
        print("No trades executed.")
        return
        
    total_wins = res_df['is_win'].sum()
    total_losses = len(res_df) - total_wins
    total_wr = (total_wins / len(res_df)) * 100
    total_pnl = (total_wins * (tp_pct - maker_fee*2*100)) - (total_losses * (sl_pct + maker_fee*2*100))
    
    print(f"TOTAL TRADES (4 YEARS): {len(res_df)}")
    print(f"TOTAL WINS: {total_wins} | TOTAL LOSSES: {total_losses}")
    print(f"OVERALL WIN RATE: {total_wr:.2f}%")
    print(f"OVERALL NET PNL: +{total_pnl:.2f}% (Average ~{total_pnl/4:.2f}% / Year)\n")
    
    print("=== YEARLY BREAKDOWN ===")
    for year in sorted(res_df['year'].unique()):
        y_df = res_df[res_df['year'] == year]
        yw = y_df['is_win'].sum()
        yl = len(y_df) - yw
        ywr = (yw / len(y_df)) * 100 if len(y_df) > 0 else 0
        ypnl = (yw * (tp_pct - maker_fee*2*100)) - (yl * (sl_pct + maker_fee*2*100))
        yvnd = ypnl * 5 # 100M * 5x
        print(f"[{year}] Trades: {len(y_df):>3} | Wins: {yw:>3} | Losses: {yl:>2} | WinRate: {ywr:>5.1f}% | NetPnL: {'+'+str(round(ypnl,2)) if ypnl>0 else round(ypnl,2)}% | VND (x5): {'+'+str(round(yvnd,1)) if yvnd>0 else round(yvnd,1)} Tr")

asyncio.run(run())
