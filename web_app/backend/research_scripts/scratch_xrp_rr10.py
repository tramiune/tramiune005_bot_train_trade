import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    print("Loading XRPUSDT 5m data...")
    df = bt_data.load("XRPUSDT", "5m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    
    c = df["close"].values
    h = df["high"].values
    l = df["low"].values
    v = df["volume"].values
    dts = df.index
    n = len(c)
    
    print("Calculating Nadaraya-Watson (h=8, mult=3.0)...")
    window = 100
    h_param = 8
    i_arr = np.arange(window)
    weights = np.exp(-(i_arr**2) / (2 * h_param**2))
    weights /= np.sum(weights)
    
    # Causal convolution: smoothed[t] = sum(weights[i] * c[t-i])
    # np.convolve(c, weights, mode='full') will align such that the index t of result is the dot product.
    smoothed = np.convolve(c, weights, mode='full')[:n]
    smoothed[:window-1] = np.nan # Match the loop behavior
    
    # mae = mean abs error over 100 periods
    err = np.abs(c - smoothed)
    mae = pd.Series(err).rolling(window).mean().values
    nada_low = smoothed - (3.0 * mae)
    
    print("Calculating RSI and Volume...")
    delta = pd.Series(c).diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.values
    
    vol_ma = pd.Series(v).rolling(20).mean().values
    
    tp_pct = 10.0
    sl_pct = 1.0
    fee = 0.05 / 100
    
    trades = []
    in_pos = False
    tp_price = 0; sl_price = 0; entry_time = None
    
    print("Đang quét lệnh (TP 10.0%, SL 1.0%)...")
    for i in range(200, n-1):
        if not in_pos:
            # Condition: Touch nada_low, RSI < 20 or RSI < 30? SKILL says RSI 20/80
            if l[i] <= nada_low[i] and c[i] > nada_low[i]:
                if rsi[i] < 20 and v[i] < (2.0 * vol_ma[i]):
                    in_pos = True
                    entry_p = c[i]
                    entry_time = dts[i]
                    tp_price = entry_p * (1 + tp_pct/100)
                    sl_price = entry_p * (1 - sl_pct/100)
        else:
            if l[i] <= sl_price:
                trades.append({'Vào Lệnh': entry_time, 'Chốt Lệnh': dts[i], 'Lãi/Lỗ': -1})
                in_pos = False
            elif h[i] >= tp_price:
                trades.append({'Vào Lệnh': entry_time, 'Chốt Lệnh': dts[i], 'Lãi/Lỗ': 10})
                in_pos = False

    df_res = pd.DataFrame(trades)
    
    print("\n" + "="*60)
    print("🚀 BÁO CÁO: XRP 5M - NADARAYA WATSON (RR 1 ĂN 10)")
    print("Cấu hình: Bắt Đáy (Oversold), Cắt lỗ 1%, Chốt lời 10%")
    print("="*60)
    
    if len(df_res) == 0:
        print("Không có lệnh nào!")
        return
        
    wins = len(df_res[df_res['Lãi/Lỗ'] > 0])
    losses = len(df_res[df_res['Lãi/Lỗ'] <= 0])
    
    print(f"Tổng Lệnh (4 Năm): {len(df_res)} lệnh")
    print(f"Lệnh Thắng: {wins} | Lệnh Thua: {losses}")
    print(f"Win Rate: {wins/len(df_res)*100:.1f}%")
    print(f"Lợi nhuận ròng: +{df_res['Lãi/Lỗ'].sum()} R")
    
    print("\n--- SAO KÊ 10 LỆNH GẦN NHẤT ---")
    for idx, row in df_res.tail(10).iterrows():
        stt = "WIN  (+10 R) 🏆" if row['Lãi/Lỗ'] > 0 else "LOSS (-1 R) 🩸"
        print(f"{row['Vào Lệnh'].strftime('%Y-%m-%d %H:%M')} | {stt} | Thoát: {row['Chốt Lệnh'].strftime('%Y-%m-%d %H:%M')}")

run()
