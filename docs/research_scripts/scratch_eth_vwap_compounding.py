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
    # Win multiplier: e.g. 1 + 2.46%
    # Loss multiplier: e.g. 1 - 3.07%
    win_mult = 1 + (tp_pct/100 - maker_fee*2) 
    loss_mult = 1 - (sl_pct/100 + maker_fee + taker_fee)
    
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
                    "is_win": is_win
                })
                i = exit_idx
            else:
                i += 1
            continue
        i += 1
            
    res_df = pd.DataFrame(trades)
    
    # Simulation: Risk 10% per trade (Compounding)
    # This means Size = (Account_Balance * 0.10) / 0.03
    # Effectively Size = Account_Balance * 3.333
    
    initial_balance = 400.0 # $400 (~10 mil VND)
    risk_pct = 10.0 / 100
    stop_loss_pct = 3.0 / 100
    
    # We win 2.46% on the SIZE, we lose 3.07% on the SIZE
    win_pct_on_size = (tp_pct/100 - maker_fee*2)
    loss_pct_on_size = (sl_pct/100 + maker_fee + taker_fee)
    
    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown_pct = 0.0
    
    history = []
    
    is_liquidated = False
    
    for idx, row in res_df.iterrows():
        # Size = Risk / SL_pct
        size = (balance * risk_pct) / stop_loss_pct
        
        if row['is_win']:
            profit = size * win_pct_on_size
            balance += profit
        else:
            loss = size * loss_pct_on_size
            balance -= loss
            
        if balance > peak_balance:
            peak_balance = balance
            
        dd_pct = (peak_balance - balance) / peak_balance * 100
        if dd_pct > max_drawdown_pct:
            max_drawdown_pct = dd_pct
            
        history.append(balance)
        
        if balance <= 10.0: # Basically liquidated
            print(f"LIQUIDATED AT TRADE #{idx} ({row['timestamp']})")
            is_liquidated = True
            break
            
    res_df = res_df.iloc[:len(history)]
    res_df['balance'] = history
    
    print("\n" + "="*60)
    print("=== LÃI KÉP: RISK 10% TÀI KHOẢN MỖI LỆNH ===")
    print(f"Vốn ban đầu: ${initial_balance:.2f}")
    if is_liquidated:
        print(f"Trạng thái: CHÁY TÀI KHOẢN 💥")
    else:
        print(f"Số dư cuối cùng sau 4 năm: ${balance:.2f}")
    print(f"Đỉnh cao nhất từng đạt: ${peak_balance:.2f}")
    print(f"Max Drawdown (Sụt giảm lớn nhất từ đỉnh): -{max_drawdown_pct:.2f}%")
    print("="*60)

asyncio.run(run())
