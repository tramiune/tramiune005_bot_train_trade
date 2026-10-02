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
    cond_bw = df['bandwidth'] < 5.0
    
    df['long_signal'] = cond_bw & (df['datetime'].dt.hour > 0) & (df['low'] <= df['lower_2_5']) & (df['close'] > df['lower_2_5']) & (df['close'] > df['open'])
    df['short_signal'] = cond_bw & (df['datetime'].dt.hour > 0) & (df['high'] >= df['upper_2_5']) & (df['close'] < df['upper_2_5']) & (df['close'] < df['open'])
    
    tp_pct = 2.5
    sl_pct = 3.0
    maker_fee = 0.02 / 100
    taker_fee = 0.05 / 100
    
    # We will use Maker for entry (limit at band), Maker for Win exit (limit at TP), Taker for Loss exit (market stop loss)
    win_pnl = tp_pct - (maker_fee * 100) - (maker_fee * 100) # 2.5 - 0.02 - 0.02 = +2.46%
    loss_pnl = -sl_pct - (maker_fee * 100) - (taker_fee * 100) # -3.0 - 0.02 - 0.05 = -3.07%
    
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
                    "timestamp": dt,
                    "is_win": is_win,
                    "pnl": win_pnl if is_win else loss_pnl
                })
                i = exit_idx
            else:
                i += 1
            continue
        i += 1
            
    res_df = pd.DataFrame(trades)
    
    # Calculate Max Consecutive Losses
    res_df['is_loss'] = ~res_df['is_win']
    streak = res_df['is_loss'].groupby((~res_df['is_loss']).cumsum()).cumsum()
    max_losing_streak = streak.max()
    
    # Calculate Max Drawdown
    res_df['cum_pnl'] = res_df['pnl'].cumsum()
    res_df['peak'] = res_df['cum_pnl'].cummax()
    res_df['drawdown'] = res_df['cum_pnl'] - res_df['peak']
    max_drawdown = res_df['drawdown'].min()
    
    # Max Drawdown period
    worst_idx = res_df['drawdown'].idxmin()
    peak_idx = res_df.loc[:worst_idx, 'cum_pnl'].idxmax()
    start_date = res_df.loc[peak_idx, 'timestamp']
    end_date = res_df.loc[worst_idx, 'timestamp']
    
    print("\n" + "="*60)
    print("=== DRAWDOWN ANALYSIS ===")
    print(f"Max Losing Streak (Chuỗi thua liên tiếp dài nhất): {int(max_losing_streak)} lệnh")
    print(f"Max Drawdown (Sụt giảm lớn nhất): {max_drawdown:.2f}%")
    print(f"Drawdown Period: From {start_date} to {end_date}")
    print("="*60)

asyncio.run(run())
