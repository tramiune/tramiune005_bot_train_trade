import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

def calculate_causal_nadaraya_watson(close, h=8, window=100, mult=1.5):
    """
    Calculates a strictly causal Nadaraya-Watson Envelope to prevent repainting/lookahead bias.
    """
    n = len(close)
    smoothed = np.zeros(n)
    smoothed[:] = np.nan
    
    # Precompute kernel weights
    i_arr = np.arange(window)
    weights = np.exp(-(i_arr**2) / (2 * h**2))
    sum_weights = np.sum(weights)
    
    close_vals = close.values
    
    for t in range(window, n):
        # We only use past data: close[t], close[t-1], ..., close[t-window+1]
        past_closes = close_vals[t-window+1 : t+1][::-1] 
        smoothed[t] = np.sum(past_closes * weights) / sum_weights
        
    df = pd.DataFrame({'close': close, 'smoothed': smoothed})
    df['mae'] = (df['close'] - df['smoothed']).abs().rolling(window=window).mean()
    df['upper'] = df['smoothed'] + (mult * df['mae'])
    df['lower'] = df['smoothed'] - (mult * df['mae'])
    return df['smoothed'], df['upper'], df['lower']

async def fetch_data(symbol, timeframe, limit=1500, days=30):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = days * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    
    print(f"Fetching {days} days of {symbol} {timeframe} data...")
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            if not klines: break
            all_klines.extend(klines)
            # 5m = 300,000 ms
            since = klines[-1][0] + 300000 
        except:
            await asyncio.sleep(1)
    await exchange.close()
    return all_klines

async def run():
    xrp_data = await fetch_data('XRP/USDT', '5m', days=90)
    df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    print(f"Fetched {len(df)} candles. Calculating Nadaraya-Watson Envelope (Strictly Causal)...")
    
    df['nada_mid'], df['nada_up'], df['nada_low'] = calculate_causal_nadaraya_watson(df['close'], h=8, window=100, mult=1.5)
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Volume
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    
    tp_pct = 1.0
    sl_pct = 0.5
    maker_fee = 0.02 / 100
    
    print("Backtesting Mean Reversion Strategy (XRP)...")
    trades = []
    
    i = 200
    while i < len(df) - 1:
        # STRATEGY CONDITIONS:
        # 1. Price crosses below Nadaraya Lower Envelope (Extreme oversold deviation)
        # 2. RSI < 35 (Momentum confirms oversold)
        # 3. Volume > Vol_MA (Capitulation spike, stopping volume)
        
        if df['low'].iloc[i] <= df['nada_low'].iloc[i] and df['close'].iloc[i] > df['nada_low'].iloc[i]:
            if df['rsi'].iloc[i] < 35:
                if df['volume'].iloc[i] > df['vol_ma'].iloc[i]:
                    
                    entry_price = df['close'].iloc[i]
                    sl = entry_price * (1 - sl_pct/100)
                    tp = entry_price * (1 + tp_pct/100)
                    
                    is_win = False; exit_idx = i
                    # 5m timeframe, max hold 1 day (288 candles)
                    for j in range(i+1, min(i+288, len(df))):
                        if df['low'].iloc[j] <= sl:
                            is_win = False; exit_idx = j; break
                        elif df['high'].iloc[j] >= tp:
                            is_win = True; exit_idx = j; break
                            
                    if exit_idx > i:
                        trades.append({"is_win": is_win, "entry_time": df['timestamp'].iloc[i]})
                        i = exit_idx
                    else:
                        i += 1
                    continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    if len(res_df) > 0:
        wins = res_df['is_win'].sum()
        losses = len(res_df) - wins
        wr = wins / len(res_df) * 100
        pnl = (wins * (tp_pct - maker_fee*2*100)) - (losses * (sl_pct + maker_fee*2*100))
        
        print(f"\n=== XRP 5m NADA + RSI + VOLUME (90 DAYS) ===")
        print(f"Total Trades: {len(res_df)}")
        print(f"Wins: {wins}, Losses: {losses}")
        print(f"Win Rate: {wr:.2f}%")
        print(f"Net Profit: +{pnl:.2f}%" if pnl > 0 else f"Net Profit: {pnl:.2f}%")
    else:
        print("No trades triggered!")

asyncio.run(run())
