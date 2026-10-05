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
    
    print("Resampling to 4H...")
    B = df.resample('4h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c, h, l, v = B["close"], B["high"], B["low"], B["volume"]
    dts = B.index
    opens = B["open"].values
    highs = B["high"].values
    lows = B["low"].values
    
    # 1. Kênh Donchian
    # Mua khi phá đỉnh 100 nến
    dc_upper_100 = h.rolling(100).max()
    # Chốt lời động (Trailing Stop) khi thủng đáy 55 nến
    dc_lower_55 = l.rolling(55).min()
    
    # 2. Tính ATR để cài Stoploss bảo vệ ban đầu (Tránh rủi ro sập hầm)
    h_c = h - c.shift()
    l_c = l - c.shift()
    tr = pd.concat([h - l, h_c.abs(), l_c.abs()], axis=1).max(axis=1)
    atr = tr.rolling(20).mean()
    
    trades = []
    in_pos = False
    entry_p = 0; sl_price = 0; entry_time = None
    fee = 0.05 / 100
    
    up100 = dc_upper_100.shift(1).values
    dn55 = dc_lower_55.shift(1).values
    atr_val = atr.shift(1).values
    
    for i in range(100, len(B)):
        if not in_pos:
            # Tín hiệu MUA: Nến 4H Breakout đỉnh 100
            if highs[i] > up100[i] and up100[i] > 0:
                in_pos = True
                # Bắt Limit/Stop Order tại ngay điểm phá đỉnh
                entry_p = max(opens[i], up100[i]) 
                entry_time = dts[i]
                # SL bảo vệ ban đầu = 2 ATR
                sl_price = entry_p - 2 * atr_val[i]
        else:
            # TRẠNG THÁI ĐANG GỒNG LÃI (HOẶC LỖ)
            # Cập nhật Trailing Stop (Đáy 55 nến). Nếu đáy này nâng cao hơn SL cũ thì cập nhật
            current_trail = dn55[i]
            if current_trail > sl_price:
                sl_price = current_trail
                
            # Kiểm tra chạm Stoploss (Cắt lỗ ban đầu hoặc Chốt lời động)
            if lows[i] <= sl_price:
                exit_p = min(opens[i], sl_price) # Khớp tại giá SL hoặc giá Mở cửa (Nếu Gap)
                pnl_pct = ((exit_p - entry_p) / entry_p) * 100
                trades.append({'time': entry_time, 'exit': dts[i], 'pnl': pnl_pct - fee*200})
                in_pos = False
                
    res_df = pd.DataFrame(trades)
    res_df['year'] = res_df['exit'].dt.year
    res_df['month'] = res_df['exit'].dt.month
    
    print("\n=== ĐẠI TƯỚNG DONCHIAN 4H (CHUYÊN GIA ÔM TREND DOGE) ===")
    print("Vào Lệnh: Phá đỉnh 100 Nến 4H")
    print("Thoát Lệnh (Trailing Stop): Thủng đáy 55 Nến 4H")
    
    wr = (res_df['pnl'] > 0).mean() * 100
    print(f"\nTổng số lệnh (4 năm): {len(res_df)}")
    print(f"Win Rate THỰC TẾ: {wr:.2f}% (Tỷ lệ thắng thấp là bản chất của đánh Trend)")
    print(f"Lợi Nhuận Trung Bình / Lệnh Thắng: {res_df[res_df['pnl']>0]['pnl'].mean():.2f}%")
    print(f"Lỗ Trung Bình / Lệnh Thua: {res_df[res_df['pnl']<=0]['pnl'].mean():.2f}%")
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
        
    print("\n=== SAO KÊ CHI TIẾT TỪNG THÁNG ===")
    monthly = res_df.groupby(['year', 'month']).agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    
    print("Năm-Tháng | Lệnh | Thắng | Win Rate | PnL ròng")
    print("-" * 50)
    for _, row in monthly.iterrows():
        wr_m = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])}-{int(row['month']):02d}    | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wr_m:5.1f}% | {row['pnl']:+8.2f}%")

run()
