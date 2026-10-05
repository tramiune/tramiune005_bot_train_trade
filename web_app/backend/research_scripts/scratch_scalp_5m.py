import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

def calculate_vwap(df):
    q = df['volume'] * ((df['high'] + df['low'] + df['close']) / 3)
    # For 5m, 1 day = 288 candles
    return q.rolling(window=288).sum() / df['volume'].rolling(window=288).sum()

def calculate_adx(df, period=14):
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff(-1).abs()
    
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

async def fetch_3_months_5m():
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ninety_days_ms = 90 * 24 * 60 * 60 * 1000
    since = now - ninety_days_ms
    
    all_klines = []
    print("Fetching 3 months of 5m data...")
    
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv('SOL/USDT', '5m', since=since, limit=1500)
            if not klines:
                break
            all_klines.extend(klines)
            since = klines[-1][0] + (5 * 60000)
        except Exception as e:
            print("Error fetching:", e)
            await asyncio.sleep(1)
            
    await exchange.close()
    return all_klines

async def run():
    data = await fetch_3_months_5m()
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    print(f"Fetched {len(df)} candles! Calculating indicators...")
    
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['vwap'] = calculate_vwap(df)
    
    atr = calculate_adx(df, 14)
    df['atr_pct'] = (atr / df['close']) * 100
    
    tp_pct = 1.5
    sl_pct = 0.7
    maker_fee_total = 0.02 / 100
    
    # We will test without ATR filter, and with ATR > 0.15% (since 5m ATR is higher)
    for atr_filter in [0, 0.15, 0.20]:
        wins = 0
        losses = 0
        
        i = 300
        while i < len(df) - 1:
            if df['close'].iloc[i] > df['vwap'].iloc[i]:
                if df['ema9'].iloc[i] > df['ema21'].iloc[i]:
                    if df['low'].iloc[i] <= df['ema21'].iloc[i] and df['close'].iloc[i] > df['ema21'].iloc[i]:
                        if atr_filter == 0 or df['atr_pct'].iloc[i] > atr_filter:
                            
                            entry_price = df['close'].iloc[i]
                            sl = entry_price * (1 - sl_pct/100)
                            tp = entry_price * (1 + tp_pct/100)
                            
                            is_win = False
                            exit_idx = i
                            # Lookahead 1 day = 288 candles for 5m
                            for j in range(i+1, min(i+288, len(df))):
                                if df['low'].iloc[j] <= sl:
                                    is_win = False
                                    exit_idx = j
                                    break
                                elif df['high'].iloc[j] >= tp:
                                    is_win = True
                                    exit_idx = j
                                    break
                                    
                            if exit_idx > i:
                                if is_win:
                                    wins += 1
                                else:
                                    losses += 1
                                i = exit_idx
                            else:
                                i += 1
                            continue
            i += 1
            
        total_trades = wins + losses
        wr = (wins / total_trades * 100) if total_trades > 0 else 0
        limit_pnl = (wins * (tp_pct - (maker_fee_total * 2 * 100))) - (losses * (sl_pct + (maker_fee_total * 2 * 100)))
        
        print(f"\n[ATR Filter > {atr_filter}%]")
        print(f"Total Trades: {total_trades}")
        print(f"Wins: {wins}, Losses: {losses}")
        print(f"Win Rate: {wr:.2f}%")
        print(f"Net Profit (Limit Order): +{limit_pnl:.2f}%" if limit_pnl > 0 else f"Net Profit: {limit_pnl:.2f}%")

asyncio.run(run())
