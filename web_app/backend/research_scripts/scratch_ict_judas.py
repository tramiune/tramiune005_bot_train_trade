import asyncio
import pandas as pd
import time
import ccxt.async_support as ccxt
import sys

async def fetch_data(symbol, tf='15m', years=4):
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
            since = klines[-1][0] + (15 * 60 * 1000)
        except Exception:
            await asyncio.sleep(0.5)
    await exchange.close()
    return all_klines

async def run():
    data = await fetch_data('BTC/USDT', '15m', 4)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # We will iterate day by day
    df['date'] = df['datetime'].dt.date
    
    trades = []
    
    tp_pct = 2.0
    sl_pct = 1.0
    maker_fee = 0.02 / 100
    taker_fee = 0.05 / 100
    
    dates = df['date'].unique()
    
    print("Simulating ICT Judas Swing...")
    for d in dates:
        day_data = df[df['date'] == d]
        if len(day_data) < 90:
            continue
            
        # Define Asian Session: 00:00 UTC to 06:00 UTC
        asia_data = day_data[(day_data['datetime'].dt.hour >= 0) & (day_data['datetime'].dt.hour < 6)]
        if asia_data.empty: continue
        
        asia_high = asia_data['high'].max()
        asia_low = asia_data['low'].min()
        
        # Define Action Session: 06:00 UTC to 16:00 UTC (London + NY AM)
        action_data = day_data[(day_data['datetime'].dt.hour >= 6) & (day_data['datetime'].dt.hour < 16)]
        
        swept_high = False
        swept_low = False
        
        for idx, row in action_data.iterrows():
            c = row['close']
            h = row['high']
            l = row['low']
            o = row['open']
            
            # Check for Judas Sweep of High
            if not swept_high and not swept_low:
                if h > asia_high and c < asia_high and c < o:
                    # Swept high and closed below (Bearish rejection)
                    swept_high = True
                    side = 'SHORT'
                    entry = c
                    sl = h * 1.002 # Stop slightly above the wick
                    sl_dist = (sl - entry) / entry
                    if sl_dist < 0.002: sl_dist = 0.002 # min 0.2% SL
                    tp_dist = sl_dist * 2.0 # RR 1:2
                    
                    sl_price = entry * (1 + sl_dist)
                    tp_price = entry * (1 - tp_dist)
                    
                    # Track trade
                    is_win = False
                    for j in range(idx+1, len(df)):
                        f_h = df['high'].iloc[j]
                        f_l = df['low'].iloc[j]
                        if f_h >= sl_price:
                            is_win = False; break
                        elif f_l <= tp_price:
                            is_win = True; break
                            
                    trades.append(is_win)
                    break # Only one trade per day
                    
                elif l < asia_low and c > asia_low and c > o:
                    # Swept low and closed above (Bullish rejection)
                    swept_low = True
                    side = 'LONG'
                    entry = c
                    sl = l * 0.998 # Stop slightly below wick
                    sl_dist = (entry - sl) / entry
                    if sl_dist < 0.002: sl_dist = 0.002
                    tp_dist = sl_dist * 2.0 # RR 1:2
                    
                    sl_price = entry * (1 - sl_dist)
                    tp_price = entry * (1 + tp_dist)
                    
                    is_win = False
                    for j in range(idx+1, len(df)):
                        f_h = df['high'].iloc[j]
                        f_l = df['low'].iloc[j]
                        if f_l <= sl_price:
                            is_win = False; break
                        elif f_h >= tp_price:
                            is_win = True; break
                            
                    trades.append(is_win)
                    break # Only one trade per day
                    
    w = trades.count(True)
    l = trades.count(False)
    total = w + l
    wr = (w / total) * 100 if total > 0 else 0
    
    # RR is exactly 1:2
    win_mult = 2.0 - maker_fee*100 - maker_fee*100
    loss_mult = -1.0 - maker_fee*100 - taker_fee*100
    pnl = (w * win_mult) + (l * loss_mult)
    be_wr = abs(loss_mult) / (win_mult + abs(loss_mult)) * 100
    
    print("\n" + "="*60)
    print("=== ICT JUDAS SWING (ASIAN SESSION SWEEP) ===")
    print(f"Risk/Reward: 1:2.0")
    print("="*60)
    print(f"Trades: {total:>3} | W: {w:>3} | L: {l:>3} | WR: {wr:>5.2f}% (Cần: {be_wr:.2f}%) | PnL (R): {pnl:>+6.2f} R")

asyncio.run(run())
