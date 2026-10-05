import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt
import sys

async def fetch_data(symbol, tf='5m', years=2):
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
    data = await fetch_data('ETH/USDT', '5m', 2)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    df = calculate_daily_vwap(df)
    
    # 1H EMA200 approximated on 5m = 12 * 200 = 2400
    df['ema_2400'] = df['close'].ewm(span=2400, adjust=False).mean()
    df['bandwidth'] = (df['upper_2_5'] - df['lower_2_5']) / df['vwap'] * 100
    df['vol_sma50'] = df['volume'].rolling(50).mean()
    df['atr'] = df['high'] - df['low'] # proxy atr
    df['atr_sma50'] = df['atr'].rolling(50).mean()
    
    df['long_signal'] = (df['datetime'].dt.hour > 0) & (df['low'] <= df['lower_2_5']) & (df['close'] > df['lower_2_5']) & (df['close'] > df['open'])
    df['short_signal'] = (df['datetime'].dt.hour > 0) & (df['high'] >= df['upper_2_5']) & (df['close'] < df['upper_2_5']) & (df['close'] < df['open'])
    
    tp_pct = 2.5
    sl_pct = 3.0
    
    trades = []
    i = 1
    while i < len(df) - 1:
        if df['long_signal'].iloc[i] or df['short_signal'].iloc[i]:
            side = 'LONG' if df['long_signal'].iloc[i] else 'SHORT'
            entry_price = df['close'].iloc[i]
            dt = df['datetime'].iloc[i]
            
            if side == 'LONG':
                sl_price = entry_price * (1 - sl_pct/100)
                tp_price = entry_price * (1 + tp_pct/100)
                trend_diff = (entry_price - df['ema_2400'].iloc[i]) / entry_price * 100
            else:
                sl_price = entry_price * (1 + sl_pct/100)
                tp_price = entry_price * (1 - tp_pct/100)
                trend_diff = (df['ema_2400'].iloc[i] - entry_price) / entry_price * 100
                
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
                    "side": side,
                    "hour": dt.hour,
                    "day_of_week": dt.dayofweek, # 0=Mon, 6=Sun
                    "bandwidth": df['bandwidth'].iloc[i],
                    "vol_ratio": df['volume'].iloc[i] / df['vol_sma50'].iloc[i] if df['vol_sma50'].iloc[i] > 0 else 1,
                    "trend_dist": trend_diff,
                    "atr_ratio": df['atr'].iloc[i] / df['atr_sma50'].iloc[i] if df['atr_sma50'].iloc[i] > 0 else 1
                })
                i = exit_idx
            else:
                i += 1
            continue
        i += 1
            
    res_df = pd.DataFrame(trades)
    losses_df = res_df[res_df['is_win'] == False]
    wins_df = res_df[res_df['is_win'] == True]
    
    print("\n" + "="*50)
    print("=== VWAP Z-SCORE LOSS ANALYSIS (2 YEARS) ===")
    print("="*50)
    print(f"Total Trades: {len(res_df)}")
    print(f"Total Losses: {len(losses_df)}")
    print(f"Total Wins: {len(wins_df)}")
    
    print("\n[ 1. HOUR OF DAY (UTC) DISTRIBUTION ]")
    loss_hours = losses_df['hour'].value_counts().sort_index()
    win_hours = wins_df['hour'].value_counts().sort_index()
    for h in range(1, 24):
        lc = loss_hours.get(h, 0)
        wc = win_hours.get(h, 0)
        total = lc + wc
        wr = (wc / total * 100) if total > 0 else 0
        print(f"Hour {h:02d}: {lc} losses | {wc} wins | WR: {wr:.1f}%")
        
    print("\n[ 2. BANDWIDTH AT ENTRY ]")
    print(f"Avg Bandwidth for WINS: {wins_df['bandwidth'].mean():.2f}%")
    print(f"Avg Bandwidth for LOSSES: {losses_df['bandwidth'].mean():.2f}%")
    
    print("\n[ 3. VOLUME RATIO AT ENTRY ]")
    print(f"Avg Vol Ratio for WINS: {wins_df['vol_ratio'].mean():.2f}x")
    print(f"Avg Vol Ratio for LOSSES: {losses_df['vol_ratio'].mean():.2f}x")
    
    print("\n[ 4. ATR SPIKE AT ENTRY ]")
    print(f"Avg ATR Ratio for WINS: {wins_df['atr_ratio'].mean():.2f}x")
    print(f"Avg ATR Ratio for LOSSES: {losses_df['atr_ratio'].mean():.2f}x")
    
    print("\n[ 5. DISTANCE TO EMA200 (Macro Trend) ]")
    # Positive means we traded AGAINST the trend (e.g., LONG when price is far BELOW EMA200)
    # Wait, in the code: side=LONG -> trend_diff = (entry - ema) / entry.
    # So if entry < ema, trend_diff is negative.
    print(f"Avg Trend Dist for WINS: {wins_df['trend_dist'].mean():.2f}%")
    print(f"Avg Trend Dist for LOSSES: {losses_df['trend_dist'].mean():.2f}%")

asyncio.run(run())
