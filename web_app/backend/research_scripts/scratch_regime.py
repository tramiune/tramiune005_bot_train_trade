import asyncio
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    
    # Dùng khung 1 Giờ (1H) để soi xu hướng Vĩ mô
    B = df.resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c, h, l = B["close"], B["high"], B["low"]
    
    # 1. TÍNH ADX (Average Directional Index) để đo ĐỘ MẠNH của Trend
    length = 14
    tr1 = h - l
    tr2 = (h - c.shift(1)).abs()
    tr3 = (l - c.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    up = h - h.shift(1)
    down = l.shift(1) - l
    
    pos_dm = np.where((up > down) & (up > 0), up, 0)
    neg_dm = np.where((down > up) & (down > 0), down, 0)
    
    # Dùng smoothing Wilder (hoặc EWM)
    tr_smooth = tr.ewm(alpha=1/length, adjust=False).mean()
    pos_dm_smooth = pd.Series(pos_dm).ewm(alpha=1/length, adjust=False).mean()
    neg_dm_smooth = pd.Series(neg_dm).ewm(alpha=1/length, adjust=False).mean()
    
    plus_di = 100 * (pos_dm_smooth / tr_smooth)
    minus_di = 100 * (neg_dm_smooth / tr_smooth)
    
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(alpha=1/length, adjust=False).mean()
    
    # 2. TÍNH EMA ALIGNMENT (Định hướng)
    ema20 = c.ewm(span=20, adjust=False).mean()
    ema50 = c.ewm(span=50, adjust=False).mean()
    ema200 = c.ewm(span=200, adjust=False).mean()
    
    # PHÂN LOẠI THỊ TRƯỜNG (REGIME)
    # Sideways: ADX < 25 (Trend yếu) HOẶC EMA rối nùi (20 nằm giữa 50 và 200)
    # Uptrend: ADX >= 25 VÀ EMA20 > EMA50 > EMA200
    # Downtrend: ADX >= 25 VÀ EMA20 < EMA50 < EMA200
    
    regime = []
    adx_vals = adx.values
    e20 = ema20.values
    e50 = ema50.values
    e200 = ema200.values
    
    for i in range(len(B)):
        if adx_vals[i] < 25:
            regime.append("SIDEWAYS")
        else:
            if e20[i] > e50[i] and e50[i] > e200[i]:
                regime.append("UPTREND")
            elif e20[i] < e50[i] and e50[i] < e200[i]:
                regime.append("DOWNTREND")
            else:
                regime.append("SIDEWAYS") # Có lực nhưng các mốc hỗ trợ đang chéo nhau (Chop)
                
    regime_series = pd.Series(regime)
    counts = regime_series.value_counts(normalize=True) * 100
    
    print("=== ĐỊNH VỊ CHẾ ĐỘ THỊ TRƯỜNG (4 NĂM DOGE - KHUNG 1H) ===")
    print(f"Tổng số nến 1H: {len(B)}")
    print(f"Sideways (Đi ngang/Nhiễu): {counts.get('SIDEWAYS', 0):.2f}% thời gian")
    print(f"Uptrend (Sóng tăng mượt):  {counts.get('UPTREND', 0):.2f}% thời gian")
    print(f"Downtrend (Sóng giảm sâu): {counts.get('DOWNTREND', 0):.2f}% thời gian")

run()
