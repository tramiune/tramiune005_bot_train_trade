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
    return df['smoothed'], df['lower']

def get_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

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
        except Exception:
            await asyncio.sleep(0.5)
    await exchange.close()
    return all_klines

async def run():
    print("Fetching 1-Year Data for Dynamic SL/TP testing...")
    xrp_data = await fetch_data('XRP/USDT', years=1)
    btc_data = await fetch_data('BTC/USDT', years=1)
    
    df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    btc_df = btc_df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df = pd.merge(df, btc_df[['timestamp', 'close']], on='timestamp', how='inner', suffixes=('', '_btc'))
    
    df['nada_center'], df['nada_low'] = calculate_causal_nadaraya_watson(df['close'], h=8, window=100, mult=1.5)
    df['atr'] = get_atr(df['high'], df['low'], df['close'])
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    df['btc_ema200'] = df['close_btc'].ewm(span=200, adjust=False).mean()
    
    trades = []
    
    print("Simulating trades with DYNAMIC SL/TP...")
    i = 200
    while i < len(df) - 1:
        if df['low'].iloc[i] <= df['nada_low'].iloc[i] and df['close'].iloc[i] > df['nada_low'].iloc[i]:
            if df['rsi'].iloc[i] < 40 and df['vol_ratio'].iloc[i] > 1.0:
                if df['close_btc'].iloc[i] > df['btc_ema200'].iloc[i]:
                        
                    entry_price = df['close'].iloc[i]
                    atr_val = df['atr'].iloc[i]
                    
                    # DYNAMIC TP: Target is the NADA Center Line at the time of entry
                    target_tp = df['nada_center'].iloc[i]
                    # Fallback TP if center line is too close or weird
                    if target_tp <= entry_price:
                        target_tp = entry_price + (2.0 * atr_val)
                        
                    # DYNAMIC SL: Entry - 3 * ATR
                    target_sl = entry_price - (3.0 * atr_val)
                    
                    is_win = False; exit_idx = i; exit_price = 0
                    for j in range(i+1, min(i+288, len(df))):
                        # Use dynamic moving center line? Or fixed at entry? Let's use dynamic center line as TP!
                        current_center = df['nada_center'].iloc[j]
                        if pd.isna(current_center): current_center = target_tp
                        
                        if df['low'].iloc[j] <= target_sl:
                            is_win = False; exit_idx = j; exit_price = target_sl; break
                        elif df['high'].iloc[j] >= current_center:
                            is_win = True; exit_idx = j; exit_price = current_center; break
                            
                    if exit_idx > i:
                        profit_pct = ((exit_price - entry_price) / entry_price) * 100
                        # Calculate maker fees (0.02% * 2 = 0.04%)
                        net_profit_pct = profit_pct - 0.04
                        
                        trades.append({
                            "is_win": net_profit_pct > 0, 
                            "net_profit_pct": net_profit_pct,
                            "tp_pct": ((current_center - entry_price) / entry_price) * 100 if is_win else 0,
                            "sl_pct": ((entry_price - target_sl) / entry_price) * 100 if not is_win else 0
                        })
                        i = exit_idx
                    else:
                        i += 1
                    continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    wins = res_df[res_df['is_win'] == True]
    losses = res_df[res_df['is_win'] == False]
    
    wr = len(wins) / len(res_df) * 100 if len(res_df) > 0 else 0
    total_pnl = res_df['net_profit_pct'].sum()
    
    print("\n" + "="*50)
    print("=== DYNAMIC SL/TP (1-YEAR TEST) ===")
    print("SL = 3.0 * ATR | TP = Revert to NADA Center Line")
    print("="*50)
    print(f"Total Trades: {len(res_df)}")
    print(f"Wins: {len(wins)} | Losses: {len(losses)}")
    print(f"Win Rate: {wr:.2f}%")
    print(f"Avg Win %: {wins['net_profit_pct'].mean():.2f}%")
    print(f"Avg Loss %: {losses['net_profit_pct'].mean():.2f}%")
    print(f"Net PnL: {total_pnl:.2f}%")
    
    print("\nReminder of FIXED SL/TP (1.5 TP / 3.0 SL) on 1 Year:")
    print("Total Trades: ~258 | Win Rate: ~70% | Net PnL: ~+35%")
    
asyncio.run(run())
