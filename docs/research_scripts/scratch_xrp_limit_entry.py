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
    print("Fetching 1 Year XRP & BTC Data...")
    xrp_data = await fetch_data('XRP/USDT')
    btc_data = await fetch_data('BTC/USDT')
    
    df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    btc_df = btc_df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df = pd.merge(df, btc_df[['timestamp', 'close']], on='timestamp', how='inner', suffixes=('', '_btc'))
    
    print("Calculating Indicators...")
    df['nada_low'] = calculate_causal_nadaraya_watson(df['close'], h=8, window=100, mult=1.5)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    
    df['btc_ema200'] = df['close_btc'].ewm(span=200, adjust=False).mean()
    
    maker_fee = 0.02 / 100
    rsi_limit = 40; vol_limit = 1.0
    
    print("\nTesting Delayed Sniper Entries (RR 1:1)...")
    
    for wait_drop_pct in [0.75, 1.0, 1.5]:
        trades = []
        i = 500
        while i < len(df) - 1:
            if df['low'].iloc[i] <= df['nada_low'].iloc[i] and df['close'].iloc[i] > df['nada_low'].iloc[i]:
                if df['rsi'].iloc[i] < rsi_limit and df['vol_ratio'].iloc[i] > vol_limit:
                    if df['close_btc'].iloc[i] > df['btc_ema200'].iloc[i]:
                        
                        signal_price = df['close'].iloc[i]
                        limit_entry_price = signal_price * (1 - wait_drop_pct/100)
                        
                        # Set RR 1:1 from the actual Limit Entry Price!
                        # We use 1.5% TP and 1.5% SL
                        tp_pct = 1.5
                        sl_pct = 1.5
                        
                        is_filled = False
                        fill_idx = -1
                        
                        # Wait up to 12 candles (1 hour) for the limit order to fill
                        for w in range(i+1, min(i+13, len(df))):
                            if df['low'].iloc[w] <= limit_entry_price:
                                is_filled = True
                                fill_idx = w
                                break
                        
                        if is_filled:
                            # Now track the trade from fill_idx
                            sl = limit_entry_price * (1 - sl_pct/100)
                            tp = limit_entry_price * (1 + tp_pct/100)
                            is_win = False
                            exit_idx = fill_idx
                            
                            for j in range(fill_idx+1, min(fill_idx+288, len(df))):
                                if df['low'].iloc[j] <= sl:
                                    is_win = False; exit_idx = j; break
                                elif df['high'].iloc[j] >= tp:
                                    is_win = True; exit_idx = j; break
                            
                            if exit_idx > fill_idx:
                                trades.append({"is_win": is_win})
                                i = exit_idx
                                continue
                        
                        # If not filled, or trade tracked, just skip past the signal
            i += 1
            
        res_df = pd.DataFrame(trades)
        total_filled = len(res_df)
        if total_filled > 0:
            wins = res_df['is_win'].sum()
            losses = total_filled - wins
            wr = wins / total_filled * 100
            pnl = (wins * (1.5 - maker_fee*2*100)) - (losses * (1.5 + maker_fee*2*100))
            
            print(f"\n[Limit Order at -{wait_drop_pct}% | TP +1.5% | SL -1.5% (RR 1:1)]")
            print(f"Total Signals: 233 | Filled Orders: {total_filled}")
            print(f"Wins: {wins} | Losses: {losses} | WinRate: {wr:.2f}%")
            print(f"Net PnL (1 Year): +{pnl:.2f}%" if pnl>0 else f"Net PnL (1 Year): {pnl:.2f}%")
        else:
            print(f"\n[Limit Order at -{wait_drop_pct}%] No orders filled.")

asyncio.run(run())
