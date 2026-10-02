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
    print(f"Fetching {years} Year(s) of {symbol} {tf} Data...")
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, tf, since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + (3 * 60 * 1000) # 3 minutes
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
    data = await fetch_data('DOGE/USDT', '3m', 4)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df = calculate_kc(df)
    df = calculate_bb(df)
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_off'] = ~df['squeeze_on']
    df['squeeze_duration'] = df['squeeze_on'].groupby((~df['squeeze_on']).cumsum()).cumsum()
    
    signals = []
    i = 200
    while i < len(df) - 1:
        was_squeezed = df['squeeze_duration'].iloc[i-1] >= 5
        fires_now = df['squeeze_off'].iloc[i] and df['squeeze_on'].iloc[i-1]
        high_vol = df['volume'].iloc[i] > (1.5 * df['vol_ma'].iloc[i])
        
        if was_squeezed and fires_now and high_vol:
            is_bullish_breakout = df['close'].iloc[i] > df['bb_mid'].iloc[i]
            side = 'SHORT' if is_bullish_breakout else 'LONG'
            signals.append({
                'idx': i,
                'side': side,
                'entry': df['close'].iloc[i]
            })
        i += 1

    tps = [2.0, 3.0, 4.0, 5.0, 6.0]
    sls = [5.0, 8.0, 10.0, 12.0, 15.0]
    
    maker_fee = 0.02 / 100
    taker_fee = 0.05 / 100
    
    results = []
    print("\n--- OPTIMIZING INVERSE BREAKOUT CHO DOGE/USDT KHUNG 3 PHÚT (3m) ---")
    
    for tp_pct in tps:
        for sl_pct in sls:
            if sl_pct <= tp_pct: continue
            
            trades = []
            curr_signal_idx = 0
            
            while curr_signal_idx < len(signals):
                sig = signals[curr_signal_idx]
                idx = sig['idx']
                side = sig['side']
                entry = sig['entry']
                
                if side == 'LONG':
                    sl_price = entry * (1 - sl_pct/100)
                    tp_price = entry * (1 + tp_pct/100)
                else:
                    sl_price = entry * (1 + sl_pct/100)
                    tp_price = entry * (1 - tp_pct/100)
                    
                is_win = False
                exit_idx = idx
                for j in range(idx+1, min(idx+1440, len(df))): # Look forward up to 3 days (1440 3m-candles)
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
                            
                if exit_idx > idx:
                    trades.append(is_win)
                    while curr_signal_idx < len(signals) and signals[curr_signal_idx]['idx'] <= exit_idx:
                        curr_signal_idx += 1
                else:
                    curr_signal_idx += 1
            
            w = trades.count(True)
            l = trades.count(False)
            total = w + l
            wr = (w / total) * 100 if total > 0 else 0
            
            win_mult = tp_pct - maker_fee*100 - maker_fee*100
            loss_mult = -sl_pct - maker_fee*100 - taker_fee*100
            pnl = (w * win_mult) + (l * loss_mult)
            be_wr = abs(loss_mult) / (win_mult + abs(loss_mult)) * 100
            
            results.append({
                'tp': tp_pct,
                'sl': sl_pct,
                'trades': total,
                'wr': wr,
                'be_wr': be_wr,
                'pnl': pnl
            })
            
    res_df = pd.DataFrame(results).sort_values(by='pnl', ascending=False)
    
    print("\n--- TOP 5 CẤU HÌNH NGON NHẤT CHO DOGECOIN KHUNG 3 PHÚT (3m) ---")
    for i, r in res_df.head(5).iterrows():
        print(f"TP {r['tp']:.1f}% | SL {r['sl']:.1f}% -> PnL: ${r['pnl']:>+6.2f} (WR: {r['wr']:>5.2f}% | Lệnh: {int(r['trades'])})")

asyncio.run(run())
