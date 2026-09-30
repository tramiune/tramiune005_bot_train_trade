import asyncio
import pandas as pd
import time
import ccxt.async_support as ccxt
import sys

async def fetch_data(symbol, tf='1h', years=4):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = years * 365 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, tf, since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + (3600000 if tf=='1h' else 300000)
        except Exception:
            await asyncio.sleep(0.5)
    await exchange.close()
    return all_klines

def check_btc_signal(c, h, l, o, e20, e200, ts):
    candle_range = h - l
    close_pct = (c - l) / candle_range if candle_range > 0 else 0
    candle_size_pct = (abs(c - o) / c) * 100
    
    is_uptrend = e20 > e200
    is_touching = l <= e200 and c > e200
    is_rejection = close_pct > 0.5
    is_proper_size = candle_size_pct < 2.0
    
    dt = pd.to_datetime(ts, unit='ms')
    hour = dt.hour
    is_ny_session = 12 <= hour <= 18
    
    if is_uptrend and is_touching and is_rejection and is_proper_size and is_ny_session:
        return True
    return False

async def run():
    print("Fetching 4 Years of BTC 1h Data...")
    data = await fetch_data('BTC/USDT', '1h', 4)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    df['e200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['e20'] = df['close'].ewm(span=20, adjust=False).mean()
    
    sl_pct = 1.5
    tp_pct = 3.0
    maker_fee = 0.02 / 100
    trades = []
    
    print("Simulating BTC Pullback Strategy...")
    i = 200
    while i < len(df) - 1:
        if check_btc_signal(
            df['close'].iloc[i], df['high'].iloc[i], df['low'].iloc[i], df['open'].iloc[i],
            df['e20'].iloc[i], df['e200'].iloc[i], df['timestamp'].iloc[i]
        ):
            entry_price = df['close'].iloc[i]
            sl = entry_price * (1 - sl_pct/100)
            tp = entry_price * (1 + tp_pct/100)
            
            is_win = False
            exit_idx = i
            
            for j in range(i+1, len(df)):
                if df['low'].iloc[j] <= sl:
                    is_win = False
                    exit_idx = j
                    break
                elif df['high'].iloc[j] >= tp:
                    is_win = True
                    exit_idx = j
                    break
                    
            if exit_idx > i:
                dt = df['datetime'].iloc[i]
                trades.append({
                    "is_win": is_win, 
                    "year": dt.year,
                    "month": dt.strftime('%Y-%m')
                })
                i = exit_idx
            else:
                i += 1
            continue
        i += 1
        
    res_df = pd.DataFrame(trades)
    
    if len(res_df) == 0:
        print("No trades found.")
        return
        
    wins = res_df['is_win'].sum()
    losses = len(res_df) - wins
    wr = (wins / len(res_df)) * 100
    net_pnl = (wins * (tp_pct - maker_fee*2*100)) - (losses * (sl_pct + maker_fee*2*100))
    
    print("\n" + "="*50)
    print("=== BTC PULLBACK RR 1:2 (1 HOUR) - 4 YEARS ===")
    print("="*50)
    print(f"Total Trades: {len(res_df)}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {wr:.2f}%")
    print(f"Net PnL (SL 1.5, TP 3.0): {net_pnl:.2f}%\n")
    
    for year in sorted(res_df['year'].unique()):
        y_df = res_df[res_df['year'] == year]
        y_wins = y_df['is_win'].sum()
        y_losses = len(y_df) - y_wins
        y_wr = (y_wins / len(y_df)) * 100
        y_pnl = (y_wins * (tp_pct - maker_fee*2*100)) - (y_losses * (sl_pct + maker_fee*2*100))
        print(f"[{year}] Trades: {len(y_df)} | WinRate: {y_wr:.1f}% | PnL: {y_pnl:.2f}%")
        
asyncio.run(run())
