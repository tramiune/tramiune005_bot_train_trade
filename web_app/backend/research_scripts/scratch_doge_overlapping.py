import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

async def fetch_data(symbol, tf='3m', years=4):
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
            since = klines[-1][0] + (3 * 60 * 1000)
        except Exception:
            await asyncio.sleep(0.5)
    await exchange.close()
    return all_klines

async def run():
    print("Fetching data...")
    data = await fetch_data('DOGE/USDT', '3m', 4)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    period = 20
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift()))
    )
    df['atr'] = df['tr'].rolling(window=period).mean()
    df['kc_mid'] = df['close'].rolling(window=period).mean()
    df['kc_upper'] = df['kc_mid'] + (1.5 * df['atr'])
    df['kc_lower'] = df['kc_mid'] - (1.5 * df['atr'])
    
    df['bb_mid'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_mid'] + (2.0 * df['bb_std'])
    df['bb_lower'] = df['bb_mid'] - (2.0 * df['bb_std'])
    
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_off'] = ~df['squeeze_on']
    df['squeeze_duration'] = df['squeeze_on'].groupby((~df['squeeze_on']).cumsum()).cumsum()
    
    trades = []
    tp_pct = 5.0
    sl_pct = 15.0
    
    entry_fee = 0.05 / 100
    tp_fee = 0.02 / 100
    sl_fee = 0.05 / 100
    
    print("Simulating overlapping trades...")
    i = 200
    while i < len(df) - 1:
        was_squeezed = df['squeeze_duration'].iloc[i-1] >= 5
        fires_now = df['squeeze_off'].iloc[i] and df['squeeze_on'].iloc[i-1]
        high_vol = df['volume'].iloc[i] > (1.5 * df['vol_ma'].iloc[i])
        
        if was_squeezed and fires_now and high_vol:
            is_bullish_breakout = df['close'].iloc[i] > df['bb_mid'].iloc[i]
            side = 'SHORT' if is_bullish_breakout else 'LONG'
            entry = df['close'].iloc[i]
            
            if side == 'LONG':
                sl_price = entry * (1 - sl_pct/100)
                tp_price = entry * (1 + tp_pct/100)
            else:
                sl_price = entry * (1 + sl_pct/100)
                tp_price = entry * (1 - tp_pct/100)
                
            exit_idx = i
            is_win = False
            for j in range(i+1, len(df)):
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
            
            if exit_idx == i: # mark to market
                exit_price = df['close'].iloc[-1]
                is_win = (exit_price > entry) if side == 'LONG' else (exit_price < entry)
                if is_win:
                    actual_pct = (exit_price - entry)/entry if side=='LONG' else (entry - exit_price)/entry
                    pnl = actual_pct - entry_fee - tp_fee
                else:
                    actual_pct = (entry - exit_price)/entry if side=='LONG' else (exit_price - entry)/entry
                    pnl = actual_pct - entry_fee - sl_fee
                trades.append(pnl)
            else:
                if is_win:
                    pnl = tp_pct/100 - entry_fee - tp_fee
                else:
                    pnl = -sl_pct/100 - entry_fee - sl_fee
                trades.append(pnl)
            
            # NO "i = exit_idx" (ALLOW OVERLAPPING TRADES)
            
        i += 1
        
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    wr = len(wins) / len(trades) * 100 if trades else 0
    total_pnl = sum(trades) * 100 # In percent
    
    print(f"Total Trades (Overlapping Allowed): {len(trades)}")
    print(f"Win Rate: {wr:.2f}% ({len(wins)}W / {len(losses)}L)")
    print(f"Total Gross/Net PnL (%): {total_pnl:.2f}%")
    print(f"Average PnL per trade: {(sum(trades)*100)/len(trades):.4f}%")

asyncio.run(run())
