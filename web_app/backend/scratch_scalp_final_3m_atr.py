import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

def calculate_vwap(df):
    q = df['volume'] * ((df['high'] + df['low'] + df['close']) / 3)
    return q.rolling(window=1440).sum() / df['volume'].rolling(window=1440).sum()

def calculate_adx(df, period=14):
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff(-1).abs()
    
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

async def run():
    # Since we already fetched 3 months in the previous script, we can just fetch it again,
    # but actually we don't have it saved on disk. We have to fetch again.
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ninety_days_ms = 90 * 24 * 60 * 60 * 1000
    since = now - ninety_days_ms
    all_klines = []
    
    print("Fetching 3 months...")
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv('SOL/USDT', '1m', since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + 60000
        except:
            await asyncio.sleep(1)
    await exchange.close()
    
    df = pd.DataFrame(all_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['vwap'] = calculate_vwap(df)
    
    atr = calculate_adx(df, 14)
    df['atr_pct'] = (atr / df['close']) * 100
    
    tp_pct = 1.5
    sl_pct = 0.7
    maker_fee_total = 0.02 / 100
    wins = 0; losses = 0
    
    i = 1500
    while i < len(df) - 1:
        if df['close'].iloc[i] > df['vwap'].iloc[i]:
            if df['ema9'].iloc[i] > df['ema21'].iloc[i]:
                if df['low'].iloc[i] <= df['ema21'].iloc[i] and df['close'].iloc[i] > df['ema21'].iloc[i]:
                    
                    entry_price = df['close'].iloc[i]
                    vwap_dist = ((entry_price - df["vwap"].iloc[i]) / df["vwap"].iloc[i]) * 100
                    hour = pd.to_datetime(df["timestamp"].iloc[i], unit='ms').hour
                    atr_val = df['atr_pct'].iloc[i]
                    
                    # COMBINE ALL 3 ULTIMATE FILTERS:
                    if vwap_dist > 0.8 and (12 <= hour <= 18) and atr_val > 0.1:
                        
                        sl = entry_price * (1 - sl_pct/100)
                        tp = entry_price * (1 + tp_pct/100)
                        
                        is_win = False
                        exit_idx = i
                        for j in range(i+1, min(i+1440, len(df))):
                            if df['low'].iloc[j] <= sl:
                                is_win = False
                                exit_idx = j
                                break
                            elif df["high"].iloc[j] >= tp:  # Typo here, should be iloc
                                pass
                        
                        # Fix inner loop explicitly without typo
                        for j in range(i+1, min(i+1440, len(df))):
                            if df['low'].iloc[j] <= sl:
                                is_win = False
                                exit_idx = j
                                break
                            elif df['high'].iloc[j] >= tp:
                                is_win = True
                                exit_idx = j
                                break
                                
                        if exit_idx > i:
                            if is_win: wins += 1
                            else: losses += 1
                            i = exit_idx
                        else:
                            i += 1
                        continue
        i += 1
        
    total_trades = wins + losses
    wr = (wins / total_trades * 100) if total_trades > 0 else 0
    limit_pnl = (wins * (tp_pct - (maker_fee_total * 2 * 100))) - (losses * (sl_pct + (maker_fee_total * 2 * 100)))
    
    print("\n=== COMBINED FILTER ON 3 MONTHS (SOL 1M) ===")
    print(f"Total Trades: {total_trades}")
    print(f"Wins: {wins}, Losses: {losses}")
    print(f"Win Rate: {wr:.2f}%")
    print(f"Net Profit: +{limit_pnl:.2f}%")

asyncio.run(run())
