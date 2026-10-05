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
    count = 0
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, tf, since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + 300000
            count += 1
            if count % 10 == 0:
                print(f"[{symbol}] Fetched {len(all_klines)} candles...")
        except Exception:
            await asyncio.sleep(0.5)
    await exchange.close()
    return all_klines

def calculate_daily_vwap(df):
    df['date'] = df['datetime'].dt.date
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['vol_tp'] = df['volume'] * df['tp']
    
    # Cumulative Sums per day
    df['cum_vol'] = df.groupby('date')['volume'].cumsum()
    df['cum_vol_tp'] = df.groupby('date')['vol_tp'].cumsum()
    
    df['vwap'] = df['cum_vol_tp'] / df['cum_vol']
    
    # Variance and Standard Deviation
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
    
    print("Calculating Daily Anchored VWAP + SD Bands...")
    df = calculate_daily_vwap(df)
    
    trades = []
    sl_pct = 1.5
    maker_fee = 0.02 / 100
    
    print("Simulating VWAP Reversion Strategy...")
    # Track trade state
    in_trade = False
    trade_side = None
    entry_price = 0
    sl_price = 0
    entry_time = None
    
    for i in range(1, len(df)):
        dt = df['datetime'].iloc[i]
        
        # We process exits first
        if in_trade:
            if trade_side == 'LONG':
                if df['low'].iloc[i] <= sl_price:
                    trades.append({"side": "LONG", "is_win": False, "pnl": -sl_pct - (maker_fee*2*100), "month": dt.strftime('%Y-%m')})
                    in_trade = False
                elif df['high'].iloc[i] >= df['vwap'].iloc[i]:
                    profit = ((df['vwap'].iloc[i] - entry_price) / entry_price) * 100
                    trades.append({"side": "LONG", "is_win": profit > 0, "pnl": profit - (maker_fee*2*100), "month": dt.strftime('%Y-%m')})
                    in_trade = False
                    
            elif trade_side == 'SHORT':
                if df['high'].iloc[i] >= sl_price:
                    trades.append({"side": "SHORT", "is_win": False, "pnl": -sl_pct - (maker_fee*2*100), "month": dt.strftime('%Y-%m')})
                    in_trade = False
                elif df['low'].iloc[i] <= df['vwap'].iloc[i]:
                    profit = ((entry_price - df['vwap'].iloc[i]) / entry_price) * 100
                    trades.append({"side": "SHORT", "is_win": profit > 0, "pnl": profit - (maker_fee*2*100), "month": dt.strftime('%Y-%m')})
                    in_trade = False
            continue
            
        # Entry Logic
        # Skip the first hour of the day (VWAP bands are too narrow)
        if dt.hour == 0:
            continue
            
        c = df['close'].iloc[i]
        o = df['open'].iloc[i]
        l = df['low'].iloc[i]
        h = df['high'].iloc[i]
        
        upper = df['upper_2_5'].iloc[i]
        lower = df['lower_2_5'].iloc[i]
        
        # LONG CONDITION
        # Dropped below lower band, but closed inside, and is a green candle
        if l <= lower and c > lower and c > o:
            in_trade = True
            trade_side = 'LONG'
            entry_price = c
            sl_price = entry_price * (1 - sl_pct/100)
            entry_time = dt
            
        # SHORT CONDITION
        # Spiked above upper band, but closed inside, and is a red candle
        elif h >= upper and c < upper and c < o:
            in_trade = True
            trade_side = 'SHORT'
            entry_price = c
            sl_price = entry_price * (1 + sl_pct/100)
            entry_time = dt

    res_df = pd.DataFrame(trades)
    if len(res_df) == 0:
        print("No trades found.")
        return
        
    wins = len(res_df[res_df['is_win'] == True])
    losses = len(res_df[res_df['is_win'] == False])
    wr = (wins / len(res_df)) * 100
    total_pnl = res_df['pnl'].sum()
    
    print("\n" + "="*50)
    print("=== ETH/USDT 5M VWAP Z-SCORE REVERSION (1 YEAR) ===")
    print("="*50)
    print(f"Total Trades: {len(res_df)}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {wr:.2f}%")
    print(f"Avg Win PnL: {res_df[res_df['pnl'] > 0]['pnl'].mean():.2f}%")
    print(f"Avg Loss PnL: {res_df[res_df['pnl'] < 0]['pnl'].mean():.2f}%")
    print(f"Total Net PnL (Fixed Size 1x): {total_pnl:.2f}%\n")
    
    print("--- MONTHLY BREAKDOWN ---")
    for month in sorted(res_df['month'].unique()):
        m_df = res_df[res_df['month'] == month]
        m_wins = len(m_df[m_df['is_win'] == True])
        m_losses = len(m_df[m_df['is_win'] == False])
        m_wr = (m_wins / len(m_df)) * 100 if len(m_df) > 0 else 0
        m_pnl = m_df['pnl'].sum()
        print(f"[{month}] Trades: {len(m_df):>3} | WinRate: {m_wr:>5.1f}% | PnL: {m_pnl:>6.2f}%")

asyncio.run(run())
