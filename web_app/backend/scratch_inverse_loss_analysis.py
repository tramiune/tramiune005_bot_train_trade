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
    
    df = calculate_kc(df)
    df = calculate_bb(df)
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['vol_mult'] = df['volume'] / df['vol_ma']
    
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_off'] = ~df['squeeze_on']
    df['squeeze_duration'] = df['squeeze_on'].groupby((~df['squeeze_on']).cumsum()).cumsum()
    
    tp_pct = 2.0
    sl_pct = 5.0
    
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
            is_counter_trend = (side == 'SHORT' and trend_is_bullish) or (side == 'LONG' and not trend_is_bullish)
            
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
                    'side': side,
                    'counter_trend': is_counter_trend,
                    'hour': df['datetime'].iloc[i].hour,
                    'vol_mult': df['vol_mult'].iloc[i]
                })
                i = exit_idx
                continue
        i += 1
        
    res = pd.DataFrame(trades)
    wins = res[res['win'] == True]
    losses = res[res['win'] == False]
    
    print("\n=== ĐẶC ĐIỂM CỦA CÁC LỆNH THUA (LOSS ANALYSIS) ===")
    print(f"Tổng Lệnh: {len(res)} | Thắng: {len(wins)} | Thua: {len(losses)}")
    
    # Analyze Trend
    print("\n[1] Lọc theo Xu hướng (Trend)")
    ct_trades = res[res['counter_trend'] == True]
    tf_trades = res[res['counter_trend'] == False]
    print(f"- Đánh Ngược Xu Hướng (Macro Counter-Trend): WR = {len(ct_trades[ct_trades['win']==True])/len(ct_trades)*100:.1f}% (Lỗ {len(ct_trades[ct_trades['win']==False])} lệnh / Tổng {len(ct_trades)})")
    print(f"- Đánh Thuận Xu Hướng (Macro Trend Following): WR = {len(tf_trades[tf_trades['win']==True])/len(tf_trades)*100:.1f}% (Lỗ {len(tf_trades[tf_trades['win']==False])} lệnh / Tổng {len(tf_trades)})")
    
    # Analyze Volume
    print("\n[2] Lọc theo Khối lượng (Volume Spike)")
    extreme_vol = res[res['vol_mult'] > 3.0]
    normal_vol = res[(res['vol_mult'] <= 3.0) & (res['vol_mult'] > 1.5)]
    if len(extreme_vol) > 0:
        print(f"- Cột Vol Đột biến x3 lần: WR = {len(extreme_vol[extreme_vol['win']==True])/len(extreme_vol)*100:.1f}% (Lỗ {len(extreme_vol[extreme_vol['win']==False])} lệnh)")
    if len(normal_vol) > 0:
        print(f"- Cột Vol Thường x1.5-x3: WR = {len(normal_vol[normal_vol['win']==True])/len(normal_vol)*100:.1f}% (Lỗ {len(normal_vol[normal_vol['win']==False])} lệnh)")
        
    # Analyze Hour
    print("\n[3] Lọc theo Giờ (Time of Day)")
    asia = res[(res['hour'] >= 0) & (res['hour'] < 8)]
    eu_us = res[res['hour'] >= 8]
    if len(asia) > 0:
        print(f"- Phiên Á (0h-8h UTC): WR = {len(asia[asia['win']==True])/len(asia)*100:.1f}% (Lỗ {len(asia[asia['win']==False])} lệnh)")
    if len(eu_us) > 0:
        print(f"- Phiên Âu Mỹ (8h-24h UTC): WR = {len(eu_us[eu_us['win']==True])/len(eu_us)*100:.1f}% (Lỗ {len(eu_us[eu_us['win']==False])} lệnh)")

asyncio.run(run())
