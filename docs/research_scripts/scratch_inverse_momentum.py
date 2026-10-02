import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

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

def calculate_kc(df, period=20, mult=1.5):
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift()))
    )
    df['atr'] = df['tr'].rolling(window=period).mean()
    df['kc_mid'] = df['close'].rolling(window=period).mean()
    df['kc_upper'] = df['kc_mid'] + (mult * df['atr'])
    df['kc_lower'] = df['kc_mid'] - (mult * df['atr'])
    return df

def calculate_bb(df, period=20, mult=2.0):
    df['bb_mid'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_mid'] + (mult * df['bb_std'])
    df['bb_lower'] = df['bb_mid'] - (mult * df['bb_std'])
    return df

async def run():
    data = await fetch_data('BTC/USDT', '15m', 4)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df = calculate_kc(df)
    df = calculate_bb(df)
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_off'] = ~df['squeeze_on']
    df['squeeze_duration'] = df['squeeze_on'].groupby((~df['squeeze_on']).cumsum()).cumsum()
    
    # Calculate Candle Body Momentum
    df['body_size'] = abs(df['close'] - df['open'])
    df['body_atr_ratio'] = df['body_size'] / df['atr']
    
    tp_pct = 2.0
    sl_pct = 5.0
    maker_fee = 0.02 / 100
    taker_fee = 0.05 / 100
    
    trades = []
    i = 200
    while i < len(df) - 1:
        was_squeezed = df['squeeze_duration'].iloc[i-1] >= 5
        fires_now = df['squeeze_off'].iloc[i] and df['squeeze_on'].iloc[i-1]
        high_vol = df['volume'].iloc[i] > (1.5 * df['vol_ma'].iloc[i])
        
        if was_squeezed and fires_now and high_vol:
            is_bullish_breakout = df['close'].iloc[i] > df['bb_mid'].iloc[i]
            side = 'SHORT' if is_bullish_breakout else 'LONG'
            entry = df['close'].iloc[i]
            momentum = df['body_atr_ratio'].iloc[i]
            
            if side == 'LONG':
                sl_price = entry * (1 - sl_pct/100)
                tp_price = entry * (1 + tp_pct/100)
            else:
                sl_price = entry * (1 + sl_pct/100)
                tp_price = entry * (1 - tp_pct/100)
                
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
                    'win': is_win,
                    'momentum': momentum
                })
                i = exit_idx
                continue
        i += 1
        
    res = pd.DataFrame(trades)
    
    print("\n=== ĐỘNG LƯỢNG NẾN (CANDLE MOMENTUM) ANALYSIS ===")
    
    thresholds = [1.0, 1.5, 2.0, 2.5, 3.0]
    win_mult = tp_pct - maker_fee*100 - maker_fee*100
    loss_mult = -sl_pct - maker_fee*100 - taker_fee*100
    
    for t in thresholds:
        filtered = res[res['momentum'] <= t]
        if len(filtered) == 0: continue
        
        w = len(filtered[filtered['win'] == True])
        l = len(filtered[filtered['win'] == False])
        wr = w / len(filtered) * 100
        pnl = (w * win_mult) + (l * loss_mult)
        
        print(f"Lọc các nến có Body <= {t}x ATR: Đánh {len(filtered)} lệnh | WR {wr:.1f}% | PnL: ${pnl:+.2f}")

    print(f"\nBản Gốc (Không Lọc Động Lượng): Đánh {len(res)} lệnh | WR {len(res[res['win']]==True)/len(res)*100:.1f}% | PnL: ${(len(res[res['win']]==True) * win_mult) + (len(res[res['win']]==False) * loss_mult):+.2f}")

asyncio.run(run())
