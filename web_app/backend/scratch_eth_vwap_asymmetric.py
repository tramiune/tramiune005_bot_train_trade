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
    return df

async def run():
    data = await fetch_data('ETH/USDT', '5m', 4)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    df = calculate_daily_vwap(df)
    
    # Macro Trend
    df['ema_2400'] = df['close'].ewm(span=2400, adjust=False).mean()
    df['is_uptrend'] = df['close'] > df['ema_2400']
    
    # Asymmetric Bands
    # If Uptrend: Short needs 3.0 SD, Long needs 2.5 SD
    # If Downtrend: Short needs 2.5 SD, Long needs 3.0 SD
    df['upper_band'] = np.where(df['is_uptrend'], df['vwap'] + 3.0 * df['sd'], df['vwap'] + 2.5 * df['sd'])
    df['lower_band'] = np.where(df['is_uptrend'], df['vwap'] - 2.5 * df['sd'], df['vwap'] - 3.0 * df['sd'])
    
    df['bandwidth'] = (df['upper_band'] - df['lower_band']) / df['vwap'] * 100
    cond_bw = df['bandwidth'] < 6.0 # Slightly higher bandwidth allowed because we use 3.0 SD
    
    df['long_signal'] = cond_bw & (df['datetime'].dt.hour > 0) & (df['low'] <= df['lower_band']) & (df['close'] > df['lower_band']) & (df['close'] > df['open'])
    df['short_signal'] = cond_bw & (df['datetime'].dt.hour > 0) & (df['high'] >= df['upper_band']) & (df['close'] < df['upper_band']) & (df['close'] < df['open'])
    
    tp_pct = 2.5
    sl_pct = 3.0
    maker_fee = 0.02 / 100
    
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
                dt = df['datetime'].iloc[i]
                trades.append({
                    "month": dt.strftime('%Y-%m'),
                    "is_win": is_win
                })
                i = exit_idx
            else:
                i += 1
            continue
        i += 1
        
    trades_df = pd.DataFrame(trades)
    
    if len(trades_df) == 0:
        print("No trades")
        return
        
    w = len(trades_df[trades_df['is_win'] == True])
    l = len(trades_df) - w
    wr = w/len(trades_df)*100
    pnl = (w * (tp_pct - maker_fee*2*100)) - (l * (sl_pct + maker_fee*2*100))
    
    print("\n" + "="*60)
    print("=== ASYMMETRIC VWAP (Trend-Adjusted SD) ===")
    print("="*60)
    print(f"Trades: {len(trades_df)} | W: {w} | L: {l} | WR: {wr:.1f}% | PnL: +{pnl:.1f}%")
    
    nov_23 = trades_df[trades_df['month'] == '2023-11']
    if len(nov_23) > 0:
        w_nov = len(nov_23[nov_23['is_win'] == True])
        l_nov = len(nov_23) - w_nov
        pnl_nov = (w_nov * (tp_pct - maker_fee*2*100)) - (l_nov * (sl_pct + maker_fee*2*100))
        print(f"Tháng 11/2023: Trades {len(nov_23)} | W: {w_nov} | L: {l_nov} | PnL: {pnl_nov:.2f}%")

asyncio.run(run())
