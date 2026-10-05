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
    print("Fetching 4 years DOGE 3m data...")
    data = await fetch_data('DOGE/USDT', '3m', 4)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df = calculate_kc(df)
    df = calculate_bb(df)
    df['vol_ma'] = df['volume'].rolling(window=20).mean().shift(1)
    
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
            slippage = 0.1 / 100
            actual_entry = df['close'].iloc[i] * (1 + slippage) if side == 'LONG' else df['close'].iloc[i] * (1 - slippage)
            
            signals.append({
                'idx': i,
                'side': side,
                'entry': actual_entry
            })
        i += 1

    entry_fee = 0.05 / 100
    tp_fee = 0.02 / 100
    sl_fee = 0.05 / 100
    
    tps = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
    sls = [2.0, 3.0, 5.0, 8.0, 10.0, 12.0, 15.0, 20.0]
    
    results = []
    
    print("Testing grid...")
    for tp_pct in tps:
        for sl_pct in sls:
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
                for j in range(idx+1, len(df)):
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
                            
                if exit_idx == idx:
                    # End of data
                    exit_idx = len(df) - 1
                    exit_price = df['close'].iloc[-1]
                    is_win = (exit_price > entry) if side == 'LONG' else (exit_price < entry)
                    
                if exit_idx > idx:
                    if is_win:
                        net_pnl = tp_pct/100 - entry_fee - tp_fee
                    else:
                        net_pnl = -sl_pct/100 - entry_fee - sl_fee
                        
                    trades.append(net_pnl)
                    
                    while curr_signal_idx < len(signals) and signals[curr_signal_idx]['idx'] <= exit_idx:
                        curr_signal_idx += 1
                else:
                    curr_signal_idx += 1
                    
            w = sum(1 for p in trades if p > 0)
            l = sum(1 for p in trades if p < 0)
            total = w + l
            wr = (w / total) * 100 if total > 0 else 0
            total_pnl_pct = sum(trades) * 100
            
            results.append({
                'tp': tp_pct, 'sl': sl_pct, 'wr': wr, 'trades': total, 'pnl': total_pnl_pct
            })
            
    # Sort by PnL
    results.sort(key=lambda x: x['pnl'], reverse=True)
    
    print("Top 10 TP/SL combinations for DOGE 3m (Honest strict costs):")
    for r in results[:10]:
        print(f"TP {r['tp']}% | SL {r['sl']}% -> Win Rate {r['wr']:.1f}% | Trades {r['trades']} | Total PnL {r['pnl']:.2f}%")

asyncio.run(run())
