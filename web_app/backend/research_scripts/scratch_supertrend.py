import asyncio
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    print("Loading DOGE 1m data...")
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    
    B = df.resample('4h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c = B["close"].values
    h = B["high"].values
    l = B["low"].values
    dts = B.index
    opens = B["open"].values
    
    length = 10
    multiplier = 3.0
    
    tr1 = h - l
    tr2 = np.abs(h - np.roll(c, 1))
    tr3 = np.abs(l - np.roll(c, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = 0
    
    atr = pd.Series(tr).rolling(length).mean().values
    hl2 = (h + l) / 2
    
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    in_uptrend = np.ones(len(B), dtype=bool)
    super_trend = np.zeros(len(B))
    
    for i in range(1, len(B)):
        if c[i] > upper_band[i-1]:
            in_uptrend[i] = True
        elif c[i] < lower_band[i-1]:
            in_uptrend[i] = False
        else:
            in_uptrend[i] = in_uptrend[i-1]
            
            # Trailing logic
            if in_uptrend[i] and lower_band[i] < lower_band[i-1]:
                lower_band[i] = lower_band[i-1]
            if not in_uptrend[i] and upper_band[i] > upper_band[i-1]:
                upper_band[i] = upper_band[i-1]
                
        if in_uptrend[i]:
            super_trend[i] = lower_band[i]
        else:
            super_trend[i] = upper_band[i]
            
    # TÍN HIỆU ĐÁNH THEO SUPERTREND (Lật mặt)
    # Long khi lật sang Uptrend, Short khi lật sang Downtrend (Hoặc chỉ đánh Long)
    # Ta sẽ test CHỈ ĐÁNH LONG để công bằng với con Donchian nãy
    
    trades = []
    in_pos = False
    entry_p = 0; entry_time = None
    fee = 0.05 / 100
    
    for i in range(length, len(B)-1):
        if not in_pos:
            # Lật từ Xanh (Downtrend) sang Đỏ (Uptrend) -> MUA
            if not in_uptrend[i-1] and in_uptrend[i]:
                in_pos = True
                entry_p = opens[i+1]
                entry_time = dts[i+1]
        else:
            # Thoát vị thế khi Supertrend lật lại thành Downtrend
            if in_uptrend[i-1] and not in_uptrend[i]:
                exit_p = opens[i+1]
                pnl_pct = ((exit_p - entry_p) / entry_p) * 100
                trades.append({'time': entry_time, 'exit': dts[i+1], 'pnl': pnl_pct - fee*200})
                in_pos = False
                
    res_df = pd.DataFrame(trades)
    res_df['year'] = res_df['exit'].dt.year
    
    print("\n=== KIỂM TOÁN SUPERTREND (4H) TRÊN DOGE ===")
    print("Cấu hình: Length 10, Multiplier 3 (Chuẩn TradingView)\n")
    
    wr = (res_df['pnl'] > 0).mean() * 100
    print(f"Tổng số lệnh (4 năm): {len(res_df)}")
    print(f"Win Rate THỰC TẾ: {wr:.2f}%")
    if len(res_df[res_df['pnl']>0]) > 0:
        print(f"Lãi Trung Bình / Thắng: {res_df[res_df['pnl']>0]['pnl'].mean():.2f}%")
    if len(res_df[res_df['pnl']<=0]) > 0:
        print(f"Lỗ Trung Bình / Thua: {res_df[res_df['pnl']<=0]['pnl'].mean():.2f}%")
    print(f"Tổng Lãi Ròng Tích Lũy: {res_df['pnl'].sum():.2f}%\n")
    
    print("=== SAO KÊ TỪNG NĂM ===")
    yearly = res_df.groupby('year').agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    for _, row in yearly.iterrows():
        wr_y = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])} | {int(row['trades']):4d} lệnh | Thắng: {int(row['wins']):2d} | Win Rate: {wr_y:5.1f}% | Lãi Ròng: {row['pnl']:+7.2f}%")

run()
