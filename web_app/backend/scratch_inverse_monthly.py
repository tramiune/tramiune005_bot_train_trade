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
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['month'] = df['datetime'].dt.strftime('%Y-%m')
    
    df = calculate_kc(df)
    df = calculate_bb(df)
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_off'] = ~df['squeeze_on']
    df['squeeze_duration'] = df['squeeze_on'].groupby((~df['squeeze_on']).cumsum()).cumsum()
    
    tp_pct = 2.0
    sl_pct = 5.0
    maker_fee = 0.02 / 100
    taker_fee = 0.05 / 100
    
    win_mult = tp_pct - maker_fee*100 - maker_fee*100
    loss_mult = -sl_pct - maker_fee*100 - taker_fee*100
    
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
            trend_is_bullish = entry > df['ema_200'].iloc[i]
            
            # Unfiltered
            is_valid_unfiltered = True
            
            # Filtered: Only macro-trend aligned
            is_valid_filtered = False
            if side == 'SHORT' and not trend_is_bullish:
                is_valid_filtered = True
            elif side == 'LONG' and trend_is_bullish:
                is_valid_filtered = True
                
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
                    'month': df['month'].iloc[i],
                    'win': is_win,
                    'unfiltered': is_valid_unfiltered,
                    'filtered': is_valid_filtered
                })
                i = exit_idx
                continue
        i += 1
        
    res = pd.DataFrame(trades)
    
    months = sorted(res['month'].unique())
    
    print("\n" + "="*80)
    print(f"{'Tháng':<10} | {'CHƯA LỌC (Unfiltered)':<30} | {'ĐÃ LỌC (EMA200 Filtered)':<30}")
    print(f"{'':<10} | {'Win-Loss':<10} | {'PnL ($)':<15} | {'Win-Loss':<10} | {'PnL ($)':<15}")
    print("-" * 80)
    
    tot_u_w = 0; tot_u_l = 0; tot_u_pnl = 0
    tot_f_w = 0; tot_f_l = 0; tot_f_pnl = 0
    
    for m in months:
        m_df = res[res['month'] == m]
        
        u_df = m_df[m_df['unfiltered'] == True]
        u_w = len(u_df[u_df['win'] == True])
        u_l = len(u_df[u_df['win'] == False])
        u_pnl = (u_w * win_mult) + (u_l * loss_mult)
        
        f_df = m_df[m_df['filtered'] == True]
        f_w = len(f_df[f_df['win'] == True])
        f_l = len(f_df[f_df['win'] == False])
        f_pnl = (f_w * win_mult) + (f_l * loss_mult)
        
        tot_u_w += u_w; tot_u_l += u_l; tot_u_pnl += u_pnl
        tot_f_w += f_w; tot_f_l += f_l; tot_f_pnl += f_pnl
        
        # Only print months that had at least one filtered trade to keep output clean,
        # Or print all. We'll print all.
        u_str = f"{u_w}W - {u_l}L"
        f_str = f"{f_w}W - {f_l}L"
        
        print(f"{m:<10} | {u_str:<10} | ${u_pnl:>+10.2f}     | {f_str:<10} | ${f_pnl:>+10.2f}")
        
    print("=" * 80)
    u_tot_str = f"{tot_u_w}W - {tot_u_l}L"
    f_tot_str = f"{tot_f_w}W - {tot_f_l}L"
    print(f"{'TỔNG 4 NĂM':<10} | {u_tot_str:<10} | ${tot_u_pnl:>+10.2f}     | {f_tot_str:<10} | ${tot_f_pnl:>+10.2f}")

asyncio.run(run())
