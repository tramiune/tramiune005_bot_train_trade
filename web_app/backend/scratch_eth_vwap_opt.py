import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

async def fetch_data(symbol, tf='5m', years=1):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = years * 365 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    
    print(f"Fetching {years} Year(s) of {symbol} {tf} Data...")
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, tf, since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + 300000
        except Exception:
            await asyncio.sleep(0.5)
    await exchange.close()
    return all_klines

def calculate_daily_vwap(df):
    df['date'] = df['datetime'].dt.date
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['vol_tp'] = df['volume'] * df['tp']
    df['cum_vol'] = df.groupby('date')['volume'].cumsum()
    df['cum_vol_tp'] = df.groupby('date')['vol_tp'].cumsum()
    df['vwap'] = df['cum_vol_tp'] / df['cum_vol']
    df['dev_sq'] = df['volume'] * ((df['tp'] - df['vwap']) ** 2)
    df['cum_dev_sq'] = df.groupby('date')['dev_sq'].cumsum()
    df['variance'] = df['cum_dev_sq'] / df['cum_vol']
    df['sd'] = np.sqrt(df['variance'])
    df['upper_2_5'] = df['vwap'] + (2.5 * df['sd'])
    df['lower_2_5'] = df['vwap'] - (2.5 * df['sd'])
    return df

async def run():
    data = await fetch_data('ETH/USDT', '5m', 1)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    df = calculate_daily_vwap(df)
    
    # Pre-calculate entry signals
    print("Pre-calculating signals...")
    df['long_signal'] = (df['datetime'].dt.hour > 0) & (df['low'] <= df['lower_2_5']) & (df['close'] > df['lower_2_5']) & (df['close'] > df['open'])
    df['short_signal'] = (df['datetime'].dt.hour > 0) & (df['high'] >= df['upper_2_5']) & (df['close'] < df['upper_2_5']) & (df['close'] < df['open'])
    
    signals = df[df['long_signal'] | df['short_signal']].index.tolist()
    print(f"Found {len(signals)} raw signal candles.")
    
    maker_fee = 0.02 / 100
    
    tp_list = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    sl_list = [1.0, 1.5, 2.0, 3.0]
    
    results = []
    
    for sl_pct in sl_list:
        for tp_pct in tp_list:
            trades = []
            i = 1
            while i < len(df) - 1:
                if df['long_signal'].iloc[i] or df['short_signal'].iloc[i]:
                    side = 'LONG' if df['long_signal'].iloc[i] else 'SHORT'
                    entry_price = df['close'].iloc[i]
                    
                    if side == 'LONG':
                        sl_price = entry_price * (1 - sl_pct/100)
                        tp_price = entry_price * (1 + tp_pct/100)
                    else:
                        sl_price = entry_price * (1 + sl_pct/100)
                        tp_price = entry_price * (1 - tp_pct/100)
                        
                    is_win = False
                    exit_idx = i
                    for j in range(i+1, min(i+288, len(df))): # check within 24h max
                        if side == 'LONG':
                            if df['low'].iloc[j] <= sl_price:
                                is_win = False; exit_idx = j; break
                            elif df['high'].iloc[j] >= tp_price:
                                is_win = True; exit_idx = j; break
                        else:
                            if df['high'].iloc[j] >= sl_price:
                                is_win = False; exit_idx = j; break
                            elif df['low'].iloc[j] <= tp_price:
                                is_win = True; exit_idx = j; break
                    
                    if exit_idx > i:
                        trades.append({"is_win": is_win})
                        i = exit_idx
                    else:
                        i += 1
                    continue
                i += 1
            
            if len(trades) > 0:
                wins = sum(1 for t in trades if t['is_win'])
                losses = len(trades) - wins
                wr = (wins / len(trades)) * 100
                pnl = (wins * (tp_pct - maker_fee*2*100)) - (losses * (sl_pct + maker_fee*2*100))
                results.append((tp_pct, sl_pct, len(trades), wr, pnl))
                
    results.sort(key=lambda x: x[4], reverse=True)
    
    print("\n" + "="*50)
    print("=== TP / SL OPTIMIZATION RESULTS (VWAP Z-SCORE ETH) ===")
    print("="*50)
    print(f"{'TP %':<8} | {'SL %':<8} | {'Trades':<8} | {'WinRate':<10} | {'Net PnL':<10}")
    print("-" * 50)
    for res in results:
        tp, sl, count, wr, pnl = res
        print(f"{tp:<8.1f} | {sl:<8.1f} | {count:<8} | {wr:<9.2f}% | {pnl:+.2f}%")

asyncio.run(run())
