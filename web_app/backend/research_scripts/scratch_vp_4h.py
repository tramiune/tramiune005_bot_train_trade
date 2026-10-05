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
    
    opens = B["open"].values
    highs = B["high"].values
    lows = B["low"].values
    closes = B["close"].values
    vols = B["volume"].values
    dts = B.index
    
    # Tính Volume Profile POC mỗi 100 nến 4H (~16 ngày)
    lookback = 100
    poc_arr = np.full(len(B), np.nan)
    
    print("Đang cào dữ liệu Khối lượng (Volume Profile) trên 4H...")
    for i in range(lookback, len(B)):
        c_win = closes[i-lookback:i]
        v_win = vols[i-lookback:i]
        
        min_p = np.min(c_win)
        max_p = np.max(c_win)
        
        bins = np.linspace(min_p, max_p, 20)
        inds = np.digitize(c_win, bins) - 1
        inds = np.clip(inds, 0, 18)
        
        vol_profile = np.zeros(19)
        for j in range(lookback):
            vol_profile[inds[j]] += v_win[j]
            
        max_bin = np.argmax(vol_profile)
        poc = (bins[max_bin] + bins[max_bin+1]) / 2
        poc_arr[i] = poc

    # Tính EMA 1D (288 nến 5m, nhưng trên 4h thì 1 Ngày = 6 nến)
    # Ta lấy EMA 200 trên 4H (Tương đương xu hướng vĩ mô)
    ema = pd.Series(closes).ewm(span=200, adjust=False).mean().values
    
    tp_pct = 15.0 # TP khổng lồ
    sl_pct = 8.0  # SL rộng
    fee = 0.05 / 100
    
    trades = []
    in_pos = False
    tp_price = 0; sl_price = 0; side = 0; entry_time = None
    
    for i in range(lookback, len(B)-1):
        if not in_pos:
            poc = poc_arr[i]
            if np.isnan(poc): continue
            
            # GIĂNG BẪY GIÁ TẠI VÙNG THANH KHOẢN (POC)
            # Long: Khi giá đang trên EMA (Uptrend vĩ mô), và giá hồi về chạm POC
            if closes[i-1] > poc and lows[i] <= poc and closes[i] > ema[i]:
                in_pos = True
                side = 1
                entry_p = poc # Limit order khớp ngay POC
                entry_time = dts[i]
                tp_price = entry_p * (1 + tp_pct/100)
                sl_price = entry_p * (1 - sl_pct/100)
        else:
            if side == 1:
                if lows[i] <= sl_price:
                    trades.append({'exit': dts[i], 'pnl': -sl_pct - fee*200})
                    in_pos = False
                elif highs[i] >= tp_price:
                    trades.append({'exit': dts[i], 'pnl': tp_pct - fee*200})
                    in_pos = False

    res_df = pd.DataFrame(trades)
    if len(res_df) == 0:
        print("Không có lệnh nào!")
        return
        
    res_df['year'] = res_df['exit'].dt.year
    
    print("\n=== CHUYÊN GIA BẮT ĐÁY POC (VOLUME PROFILE 4H) ===")
    print(f"Cấu hình: TP {tp_pct}%, SL {sl_pct}% (Limit Buy tại vách đá Volume)")
    
    wr = (res_df['pnl'] > 0).mean() * 100
    print(f"\nTổng số lệnh (4 năm): {len(res_df)} (Siêu kén lệnh)")
    print(f"Win Rate: {wr:.2f}%")
    print(f"Tổng Lãi Ròng: {res_df['pnl'].sum():.2f}%\n")
    
    yearly = res_df.groupby('year').agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x > 0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    for _, row in yearly.iterrows():
        wr_y = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])} | {int(row['trades']):4d} lệnh | Thắng: {int(row['wins']):2d} | Win Rate: {wr_y:5.1f}% | Lãi Ròng: {row['pnl']:+7.2f}%")

run()
