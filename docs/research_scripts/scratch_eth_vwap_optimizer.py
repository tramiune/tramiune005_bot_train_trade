import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt
import sys

async def fetch_data(symbol, tf='5m', years=4):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = years * 365 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    
    print(f"Fetching {years} Year(s) of {symbol} {tf} Data (~4 mins)...")
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
    data = await fetch_data('ETH/USDT', '5m', 4)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    df = calculate_daily_vwap(df)
    
    df['bandwidth'] = (df['upper_2_5'] - df['lower_2_5']) / df['vwap'] * 100
    df['vol_sma50'] = df['volume'].rolling(50).mean()
    df['vol_ratio'] = df['volume'] / df['vol_sma50']
    
    # Pre-calculate base signals
    df['long_signal'] = (df['datetime'].dt.hour > 0) & (df['low'] <= df['lower_2_5']) & (df['close'] > df['lower_2_5']) & (df['close'] > df['open'])
    df['short_signal'] = (df['datetime'].dt.hour > 0) & (df['high'] >= df['upper_2_5']) & (df['close'] < df['upper_2_5']) & (df['close'] < df['open'])
    
    tp_pct = 2.5
    sl_pct = 3.0
    maker_fee = 0.02 / 100
    
    # Collect all potential trades
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
            for j in range(i+1, min(i+288, len(df))):
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
                trades.append({
                    "is_win": is_win, 
                    "bandwidth": df['bandwidth'].iloc[i],
                    "vol_ratio": df['vol_ratio'].iloc[i]
                })
                i = exit_idx
            else:
                i += 1
            continue
        i += 1
        
    trades_df = pd.DataFrame(trades)
    
    print("\n--- BASE STRATEGY ---")
    w = len(trades_df[trades_df['is_win'] == True])
    l = len(trades_df) - w
    wr = w/len(trades_df)*100 if len(trades_df) > 0 else 0
    pnl = (w * (tp_pct - maker_fee*2*100)) - (l * (sl_pct + maker_fee*2*100))
    print(f"Trades: {len(trades_df)} | W: {w} | L: {l} | WR: {wr:.1f}% | PnL: +{pnl:.1f}%")
    
    filters = [
        ("Max Bandwidth < 5.0%", trades_df['bandwidth'] < 5.0),
        ("Max Bandwidth < 4.0%", trades_df['bandwidth'] < 4.0),
        ("Max Bandwidth < 3.5%", trades_df['bandwidth'] < 3.5),
        ("Min Bandwidth > 1.0%", trades_df['bandwidth'] > 1.0),
        ("Min Bandwidth > 1.5%", trades_df['bandwidth'] > 1.5),
        ("Max Vol Ratio < 5x", trades_df['vol_ratio'] < 5.0),
        ("Max Vol Ratio < 4x", trades_df['vol_ratio'] < 4.0),
        ("Max Vol Ratio < 3x", trades_df['vol_ratio'] < 3.0),
        ("BW < 4.5 & Min BW > 1.0", (trades_df['bandwidth'] < 4.5) & (trades_df['bandwidth'] > 1.0)),
    ]
    
    print("\n--- APPLYING ISOLATED FILTERS ---")
    for name, cond in filters:
        f_df = trades_df[cond]
        w = len(f_df[f_df['is_win'] == True])
        l = len(f_df) - w
        wr = w/len(f_df)*100 if len(f_df) > 0 else 0
        pnl = (w * (tp_pct - maker_fee*2*100)) - (l * (sl_pct + maker_fee*2*100))
        print(f"{name:30} -> Trades: {len(f_df):3} | W: {w:3} | L: {l:3} | WR: {wr:4.1f}% | PnL: {pnl:+.1f}%")

asyncio.run(run())
