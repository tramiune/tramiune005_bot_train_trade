import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    print("Loading SOLUSDT 1m data...")
    df_sol = bt_data.load("SOLUSDT", "1m")
    df_sol.set_index(pd.to_datetime(df_sol['time'], unit='s'), inplace=True)
    B = df_sol.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
    
    c, h, l, v = B["close"], B["high"], B["low"], B["volume"]
    dts = B.index
    
    B["e20"] = c.ewm(span=20, adjust=False).mean()
    B["e200"] = c.ewm(span=200, adjust=False).mean()
    B["v20"] = v.rolling(20).mean()
    
    h_c = h - c.shift()
    l_c = l - c.shift()
    tr = pd.concat([h - l, h_c.abs(), l_c.abs()], axis=1).max(axis=1)
    B["atr14"] = tr.rolling(14).mean()
    
    trades = []
    last_bullish_cross_idx = 0
    
    e20 = B["e20"].values
    e200 = B["e200"].values
    v20 = B["v20"].values
    atr = B["atr14"].values
    
    rr_target = 20.0
    atr_mult = 1.0
    
    in_pos = False; entry_p = 0; sl = 0; tp = 0; entry_t = None
    
    for i in range(200, len(B)-1):
        if not in_pos:
            if e20[i-1] <= e200[i-1] and e20[i] > e200[i]:
                last_bullish_cross_idx = i
                
            candle_range = h.iloc[i] - l.iloc[i]
            close_pct = (c.iloc[i] - l.iloc[i]) / candle_range if candle_range > 0 else 0
            candle_size_pct = (candle_range / c.iloc[i]) * 100
            dt = dts[i]
            
            is_uptrend = e20[i] > e200[i]
            candles_since_cross = i - last_bullish_cross_idx
            is_proper_speed = 20 <= candles_since_cross < 150
            is_touching = l.iloc[i] <= e200[i] and c.iloc[i] > e200[i]
            is_strong_rejection = close_pct > 0.6
            has_volume = (v.iloc[i] / v20[i]) > 1.2 if v20[i] > 0 else False
            
            # GOD MODE FILTERS
            is_midweek = dt.dayofweek in [1, 2, 3] # Tue, Wed, Thu
            is_proper_session = 8 <= dt.hour <= 18
            is_proper_size = candle_size_pct < 2.5
            
            if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and has_volume and is_midweek and is_proper_session and is_proper_size:
                in_pos = True
                entry_p = c.iloc[i]
                entry_t = dt
                sl = entry_p - (atr_mult * atr[i])
                risk = entry_p - sl
                tp = entry_p + (rr_target * risk)
        else:
            hi = h.iloc[i]; lo = l.iloc[i]
            if lo <= sl:
                trades.append({'Vào Lệnh': entry_t, 'Chốt Lệnh': dts[i], 'Lãi/Lỗ': -1})
                in_pos = False
            elif hi >= tp:
                trades.append({'Vào Lệnh': entry_t, 'Chốt Lệnh': dts[i], 'Lãi/Lỗ': 20})
                in_pos = False

    df_res = pd.DataFrame(trades)
    
    print("\n" + "="*60)
    print("🚀 BÁO CÁO CẬP NHẬT: SOLANA 1H - RETEST GOD MODE (RR 20.0)")
    print("="*60)
    
    if len(df_res) == 0:
        print("Không có lệnh nào!")
        return
        
    wins = len(df_res[df_res['Lãi/Lỗ'] > 0])
    losses = len(df_res[df_res['Lãi/Lỗ'] <= 0])
    
    print(f"Tổng Lệnh (4 Năm): {len(df_res)} lệnh (Chờ đợi là Hạnh phúc)")
    print(f"Lệnh Thắng: {wins} | Lệnh Thua: {losses}")
    print(f"Win Rate: {wins/len(df_res)*100:.1f}%")
    print(f"Lợi nhuận ròng: +{df_res['Lãi/Lỗ'].sum()} R")
    
    print("\n--- SỨC MẠNH LÃI KÉP (VỐN 100 TRIỆU, ĐÁNH RISK 5%/LỆNH) ---")
    cap = 100_000_000
    risk_pct = 0.05
    
    print(f"Vốn ban đầu: {cap:,.0f} VNĐ")
    for idx, row in df_res.iterrows():
        if row['Lãi/Lỗ'] > 0:
            lãi = cap * risk_pct * 20.0
            cap += lãi
            print(f"Lệnh {idx+1:>2} | {row['Vào Lệnh'].strftime('%Y-%m-%d')} | WIN (+20R) | +{lãi:>12,.0f} đ | Dư: {cap:>15,.0f} đ")
        else:
            lỗ = cap * risk_pct
            cap -= lỗ
            print(f"Lệnh {idx+1:>2} | {row['Vào Lệnh'].strftime('%Y-%m-%d')} | LOSS (-1R) | -{lỗ:>12,.0f} đ | Dư: {cap:>15,.0f} đ")
            
    print("="*60)
    print(f"💰 TỔNG SỐ DƯ CUỐI CÙNG SAU 4 NĂM: {cap:,.0f} VNĐ")
    print("="*60)

run()
