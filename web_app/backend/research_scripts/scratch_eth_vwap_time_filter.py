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
    count = 0
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, tf, since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + 300000
            count += 1
            if count % 20 == 0:
                print(f"[{symbol}] Fetched {len(all_klines)} candles...")
                sys.stdout.flush()
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
    
    print("Calculating Daily Anchored VWAP + SD Bands...")
    df = calculate_daily_vwap(df)
    
    # Pre-calculate entry signals
    print("Pre-calculating signals...")
    # APPLIED FILTER: Ban Hour 0, 1, 2 (Only trade >= 3)
    time_filter = df['datetime'].dt.hour >= 3
    
    df['long_signal'] = time_filter & (df['low'] <= df['lower_2_5']) & (df['close'] > df['lower_2_5']) & (df['close'] > df['open'])
    df['short_signal'] = time_filter & (df['high'] >= df['upper_2_5']) & (df['close'] < df['upper_2_5']) & (df['close'] < df['open'])
    
    maker_fee = 0.02 / 100
    tp_pct = 2.5
    sl_pct = 3.0
    
    trades = []
    print("Simulating trades...")
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
                dt = df['datetime'].iloc[i]
                trades.append({
                    "is_win": is_win, 
                    "side": side,
                    "year": dt.year,
                    "month": dt.strftime('%Y-%m')
                })
                i = exit_idx
            else:
                i += 1
            continue
        i += 1
            
    res_df = pd.DataFrame(trades)
    
    wins = len(res_df[res_df['is_win'] == True])
    losses = len(res_df) - wins
    wr = (wins / len(res_df)) * 100 if len(res_df) > 0 else 0
    total_pnl = (wins * (tp_pct - maker_fee*2*100)) - (losses * (sl_pct + maker_fee*2*100))
    
    print("\n" + "="*60)
    print("=== ETH/USDT VWAP Z-SCORE (BANNED 00:00-02:00 UTC) - 4 YEARS ===")
    print("="*60)
    print(f"TOTAL TRADES: {len(res_df)}")
    print(f"WINS: {wins} | LOSSES: {losses}")
    print(f"WIN RATE: {wr:.2f}%")
    print(f"NET PNL (Fixed Size 1x): +{total_pnl:.2f}%")
    
    print("\n--- YEARLY BREAKDOWN ---")
    for year in sorted(res_df['year'].unique()):
        y_df = res_df[res_df['year'] == year]
        y_wins = len(y_df[y_df['is_win'] == True])
        y_losses = len(y_df) - y_wins
        y_pnl = (y_wins * (tp_pct - maker_fee*2*100)) - (y_losses * (sl_pct + maker_fee*2*100))
        y_wr = (y_wins / len(y_df)) * 100 if len(y_df) > 0 else 0
        print(f"[ YEAR {year} ] Trades: {len(y_df):>3} | WinRate: {y_wr:>5.1f}% | PnL: {y_pnl:+.2f}%")

asyncio.run(run())
