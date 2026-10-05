import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    print("Loading DOGE 1m data & Resampling...")
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    
    B = df.resample('5min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c, h, l, v = B["close"], B["high"], B["low"], B["volume"]
    dts = B.index
    
    # --- CALCULATE FEATURES ---
    # 1. Squeeze Mechanics
    h_c = h - c.shift()
    l_c = l - c.shift()
    tr_5m = pd.concat([h - l, h_c.abs(), l_c.abs()], axis=1).max(axis=1)
    
    a = tr_5m.rolling(20).mean()
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std()
    
    on = (mid + 2 * sd < mid + 1.5 * a) & (mid - 2 * sd > mid - 1.5 * a)
    dur = on.groupby((~on).cumsum()).cumsum()
    
    vol_mean_20 = v.rolling(20).mean()
    vol_mult = v / vol_mean_20
    
    fire = (~on) & on.shift(1, fill_value=False) & (dur.shift(1) >= 5) & (vol_mult > 1.5)
    bull = c > mid
    sig = np.where(fire, np.where(bull, 1, -1), 0)
    
    # 2. RSI 5m
    delta = c.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    rs = ema_up / ema_down
    rsi_5m = 100 - (100 / (1 + rs))
    
    # 3. EMA 1D Distance
    ema_1d = c.ewm(span=288, adjust=False).mean()
    dist_ema_1d = ((c - ema_1d) / ema_1d) * 100 # % distance
    
    # 4. ATR %
    atr_pct = (a / c) * 100
    
    # --- BACKTEST & COLLECT TRADES ---
    opens = B["open"].values
    highs = B["high"].values
    lows = B["low"].values
    
    tp_pct = 8.0
    sl_pct = 8.0
    fee = 0.05 / 100
    
    trade_data = []
    in_pos = False
    tp_price = 0; sl_price = 0; side = 0
    entry_idx = 0
    
    for i in range(288, len(B)-1):
        if not in_pos:
            if sig[i] != 0:
                in_pos = True
                side = sig[i]
                entry_idx = i
                entry_p = opens[i+1]
                if side == 1:
                    tp_price = entry_p * (1 + tp_pct/100)
                    sl_price = entry_p * (1 - sl_pct/100)
                else:
                    tp_price = entry_p * (1 - tp_pct/100)
                    sl_price = entry_p * (1 + sl_pct/100)
        else:
            is_win = None
            if side == 1:
                if lows[i] <= sl_price: is_win = False
                elif highs[i] >= tp_price: is_win = True
            else:
                if highs[i] >= sl_price: is_win = False
                elif lows[i] <= tp_price: is_win = True
                
            if is_win is not None:
                # Capture features AT THE EXACT TIME OF BREAKOUT CANDLE (entry_idx)
                trade_data.append({
                    'win': is_win,
                    'side': 'LONG' if side == 1 else 'SHORT',
                    'hour': dts[entry_idx].hour,
                    'squeeze_dur': dur.iloc[entry_idx-1], # duration before break
                    'vol_mult': vol_mult.iloc[entry_idx],
                    'rsi_5m': rsi_5m.iloc[entry_idx],
                    'dist_ema_1d': dist_ema_1d.iloc[entry_idx],
                    'atr_pct': atr_pct.iloc[entry_idx]
                })
                in_pos = False
                
    tdf = pd.DataFrame(trade_data)
    
    print("\n=== QUÉT HỒ SƠ LỆNH THẮNG vs LỆNH THUA ===")
    print(f"Tổng số lệnh: {len(tdf)}")
    print(f"Lệnh Thắng: {tdf['win'].sum()} | Lệnh Thua: {len(tdf) - tdf['win'].sum()}")
    
    # 1. Tách nhóm
    winners = tdf[tdf['win'] == True]
    losers = tdf[tdf['win'] == False]
    
    print("\n--- SO SÁNH TRUNG BÌNH CÁC CHỈ SỐ LÚC VÀO LỆNH ---")
    features = ['squeeze_dur', 'vol_mult', 'rsi_5m', 'dist_ema_1d', 'atr_pct']
    desc_names = {
        'squeeze_dur': 'T/gian Nén (Nến)',
        'vol_mult': 'Độ nổ Volume (X lần)',
        'rsi_5m': 'RSI 5 Phút',
        'dist_ema_1d': 'Khoảng cách tới EMA 1D (%)',
        'atr_pct': 'Độ biến động ATR (%)'
    }
    
    for f in features:
        w_mean = winners[f].mean()
        l_mean = losers[f].mean()
        diff = ((w_mean - l_mean) / l_mean) * 100 if l_mean != 0 else 0
        print(f"{desc_names[f]:28s} | Thắng: {w_mean:6.2f} | Thua: {l_mean:6.2f} | Chênh lệch: {diff:+6.1f}%")
        
    print("\n--- TỶ LỆ THẮNG THEO KHUNG GIỜ (UTC) ---")
    hour_stats = tdf.groupby('hour')['win'].agg(['count', 'mean']).rename(columns={'count': 'trades', 'mean': 'win_rate'})
    hour_stats['win_rate'] = hour_stats['win_rate'] * 100
    print(hour_stats.sort_values(by='win_rate', ascending=False).head(5).to_string())
    
    print("\n--- TỶ LỆ THẮNG THEO CHIỀU (LONG vs SHORT) ---")
    side_stats = tdf.groupby('side')['win'].agg(['count', 'mean']).rename(columns={'count': 'trades', 'mean': 'win_rate'})
    side_stats['win_rate'] = side_stats['win_rate'] * 100
    print(side_stats.to_string())

run()
