import asyncio
import pandas as pd
import numpy as np
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

def calculate_cmf(df, period=20):
    # Money Flow Multiplier
    mfm = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
    mfm = mfm.fillna(0.0) # avoid div by zero
    # Money Flow Volume
    mfv = mfm * df['volume']
    
    cmf = mfv.rolling(window=period).sum() / df['volume'].rolling(window=period).sum()
    df['cmf'] = cmf
    return df

def calculate_mfi(df, period=14):
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    raw_money_flow = typical_price * df['volume']
    
    pos_flow = []
    neg_flow = []
    
    for i in range(1, len(typical_price)):
        if typical_price.iloc[i] > typical_price.iloc[i-1]:
            pos_flow.append(raw_money_flow.iloc[i])
            neg_flow.append(0)
        elif typical_price.iloc[i] < typical_price.iloc[i-1]:
            pos_flow.append(0)
            neg_flow.append(raw_money_flow.iloc[i])
        else:
            pos_flow.append(0)
            neg_flow.append(0)
            
    pos_flow = pd.Series([0] + pos_flow)
    neg_flow = pd.Series([0] + neg_flow)
    
    pos_flow_sum = pos_flow.rolling(window=period).sum()
    neg_flow_sum = neg_flow.rolling(window=period).sum()
    
    money_ratio = pos_flow_sum / neg_flow_sum
    mfi = 100 - (100 / (1 + money_ratio))
    df['mfi'] = mfi.values
    return df

async def run():
    data = await fetch_data('BTC/USDT', '15m', 4)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    df = calculate_cmf(df, period=20)
    df = calculate_mfi(df, period=14)
    
    # EMA for trend filter
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # Strategy logic
    tp_pct = 3.0
    sl_pct = 1.0
    maker_fee = 0.02 / 100
    taker_fee = 0.05 / 100
    
    trades = []
    i = 200
    while i < len(df) - 1:
        # Conditions for Smart Money Breakout (Dòng tiền nổ)
        # 1. CMF spikes above 0.20 (Heavy accumulation)
        # 2. MFI > 80 (Money flow is massive)
        # 3. Price is above EMA 200
        
        is_long = (df['cmf'].iloc[i] > 0.20) and (df['cmf'].iloc[i-1] <= 0.20) and (df['mfi'].iloc[i] > 70) and (df['close'].iloc[i] > df['ema_200'].iloc[i])
        is_short = (df['cmf'].iloc[i] < -0.20) and (df['cmf'].iloc[i-1] >= -0.20) and (df['mfi'].iloc[i] < 30) and (df['close'].iloc[i] < df['ema_200'].iloc[i])
        
        if is_long or is_short:
            side = 'LONG' if is_long else 'SHORT'
            entry_price = df['close'].iloc[i]
            
            if side == 'LONG':
                sl_price = entry_price * (1 - sl_pct/100)
                tp_price = entry_price * (1 + tp_pct/100)
            else:
                sl_price = entry_price * (1 + sl_pct/100)
                tp_price = entry_price * (1 - tp_pct/100)
                
            is_win = False
            exit_idx = i
            for j in range(i+1, min(i+96, len(df))): # Look forward 24h
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
                trades.append(is_win)
                i = exit_idx
            else:
                i += 1
            continue
        i += 1
        
    w = trades.count(True)
    l = trades.count(False)
    total = w + l
    wr = (w / total) * 100 if total > 0 else 0
    
    win_mult = tp_pct - maker_fee*100 - maker_fee*100
    loss_mult = -sl_pct - maker_fee*100 - taker_fee*100
    pnl = (w * win_mult) + (l * loss_mult)
    be_wr = abs(loss_mult) / (win_mult + abs(loss_mult)) * 100
    
    print("\n" + "="*60)
    print("=== DÒNG TIỀN THÔNG MINH (CHAIKIN + MFI) ===")
    print(f"Risk/Reward: 1:{tp_pct/sl_pct} (SL: {sl_pct}%, TP: {tp_pct}%)")
    print("="*60)
    print(f"Trades: {total:>3} | W: {w:>3} | L: {l:>3} | WR: {wr:>5.2f}% (Cần: {be_wr:.2f}%) | PnL: ${pnl:>+6.2f}")

asyncio.run(run())
