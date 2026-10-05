import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
import xrp_nada as X

def run():
    print("Loading XRPUSDT 1m data...")
    d1 = bt_data.load("XRPUSDT", "1m")
    sim = H.Sim(d1)
    
    print("Resampling to 5m & Extracting Signals...")
    B = H.resample(d1, 5)
    
    # Cấu hình Vua Kỷ Lục Mới (+218 R)
    r_os, v_mult, m = 20, 2.5, 3.0
    sl_pct, tp_pct = 0.5, 15.0
    
    side = X.signals(B, h=8.0, mult=m, rsi_os=r_os, rsi_ob=100-r_os, vol_mult=v_mult)
    c = B["close"].to_numpy()
    
    T = sim.run(B, side, c * sl_pct / 100, c * tp_pct / 100)
    T['entry_time'] = pd.to_datetime(T.entry_t, unit='s')
    T['is_win'] = T['reason'] == 'TP'
    
    # 1. Tính Chuỗi Thua Liên Tiếp (Max Consecutive Losses)
    max_loss_streak = 0
    current_streak = 0
    
    for is_win in T['is_win']:
        if not is_win:
            current_streak += 1
            max_loss_streak = max(max_loss_streak, current_streak)
        else:
            current_streak = 0
            
    print(f"\n[THỐNG KÊ RỦI RO]")
    print(f"Tổng Lệnh: {len(T)} | Thắng: {T['is_win'].sum()} | Thua: {(~T['is_win']).sum()}")
    print(f"CHUỖI THUA DÀI NHẤT (Max Consecutive Losses): {max_loss_streak} lệnh")
    
    # Nếu rủi ro 2% mỗi lệnh, chuỗi thua lớn nhất âm bao nhiêu % tài khoản?
    print(f"Max Drawdown (nếu risk 1%/lệnh): -{max_loss_streak}%")
    print(f"Max Drawdown (nếu risk 2%/lệnh): -{max_loss_streak * 2}%")
    
    # 2. Các Lệnh Thắng xảy ra khi nào?
    print(f"\n[PHÂN TÍCH THỜI ĐIỂM {T['is_win'].sum()} LỆNH THẮNG]")
    wins_df = T[T['is_win']].copy()
    
    for idx, row in wins_df.iterrows():
        entry_t = row['entry_time']
        month_year = entry_t.strftime('%m-%Y')
        print(f"- Lệnh Thắng: {entry_t} | Giá bắt đáy: {row['entry']:.4f}")

run()
