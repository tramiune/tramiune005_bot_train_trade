import sys, os
import pandas as pd
import numpy as np
import time

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H

def find_fvg_signals_inverse(h, l, c, entry_type='edge', smc_rr=2.0):
    side = np.zeros(len(c), dtype=int)
    limit_px = np.full(len(c), np.nan)
    sl_px = np.full(len(c), np.nan)
    tp_px = np.full(len(c), np.nan)
    
    prev2_h = np.roll(h, 2)
    prev2_l = np.roll(l, 2)
    
    bull_fvg = (l > prev2_h) & (c > np.roll(c, 1))
    bear_fvg = (h < prev2_l) & (c < np.roll(c, 1))
    
    for i in range(2, len(c)):
        # NGƯỢC LẠI: Thấy Bullish FVG (Tụi SMC mua) thì mình BÁN KHỐNG!
        if bull_fvg[i]:
            side[i] = -1 # SHORT
            if entry_type == 'edge': limit_px[i] = prev2_h[i]
            else: limit_px[i] = (prev2_h[i] + l[i]) / 2.0
            
            # Tụi SMC đặt Cắt lỗ ở prev2_l. Mình đặt CHỐT LỜI ở đó! (Săn thanh khoản)
            tp_px[i] = prev2_l[i]
            
            risk_for_smc = limit_px[i] - prev2_l[i]
            if risk_for_smc <= 0: side[i] = 0; continue
            
            # Tụi SMC đặt Chốt lời ở trên cao. Mình đặt CẮT LỖ ở đó!
            sl_px[i] = limit_px[i] + risk_for_smc * smc_rr
            
        elif bear_fvg[i]:
            side[i] = 1 # LONG
            if entry_type == 'edge': limit_px[i] = prev2_l[i]
            else: limit_px[i] = (prev2_l[i] + h[i]) / 2.0
                
            # SMC đặt SL ở prev2_h. Mình đặt CHỐT LỜI ở đó.
            tp_px[i] = prev2_h[i]
            
            risk_for_smc = prev2_h[i] - limit_px[i]
            if risk_for_smc <= 0: side[i] = 0; continue
            
            sl_px[i] = limit_px[i] - risk_for_smc * smc_rr
            
    return side, limit_px, tp_px, sl_px

def run():
    print("Loading BTCUSDT 1m data...")
    d1 = bt_data.load("BTCUSDT", "1m")
    sim = H.Sim(d1)
    
    # Cái lỗ nhất lúc nãy: Khung 15m, Edge, SMC RR 3.0 (Lỗ -691 R)
    tf = 15
    rr = 3.0
    et = 'edge'
    
    B = H.resample(d1, tf)
    c = B["close"].to_numpy()
    h = B["high"].to_numpy()
    l = B["low"].to_numpy()
    
    valid_min = tf * 10 
    
    print("Bắt đầu Chạy Kịch Bản INVERSE SMC (Săn Thanh Khoản Đám Đông)...")
    side, limit_px, tp_px, sl_px = find_fvg_signals_inverse(h, l, c, entry_type=et, smc_rr=rr)
    
    T = sim.run_limit(B, side, limit_px, tp_px, sl_px, valid_min=valid_min, tp_limit=True)
    
    trades = len(T)
    wins = len(T[T['net'] > 0])
    wr = (wins / trades) * 100 if trades > 0 else 0
    
    # Phí giao dịch
    fee_penalty = 0.15
    
    # Vì mình đánh ngược:
    # Nếu lệnh chạm TP, mình ăn được 1 phần rủi ro của SMC (R = 1/3 vì SMC RR là 3.0)
    # Nếu lệnh chạm SL, mình thua phần rủi ro của SMC (R = 1)
    
    my_rr = 1.0 / rr # SMC ăn 3 thì rủi ro của mình là 3, mình ăn 1. Nghĩa là mình R:R = 1 : 0.33
    
    T['raw_r'] = np.where(T['reason'] == 'TP', my_rr, -1.0)
    T['net_r'] = T['raw_r'] - fee_penalty
    
    total_r = T['net_r'].sum()
    
    print("\n=== BÁO CÁO INVERSE SMC (ĐÁNH NGƯỢC) ===")
    print(f"- Thống số tụi SMC: Khung 15m, Đánh ở mép Gap, RR 1 ăn 3 (Bọn này lỗ -691 R)")
    print(f"- Số lệnh khớp: {trades}")
    print(f"- Win Rate CỦA MÌNH: {wr:.1f}%")
    print(f"- Tỷ lệ RR CỦA MÌNH: Thua thì mất 1 R, Thắng thì ăn {my_rr:.2f} R")
    print(f"- TỔNG LÃI NHẬN ĐƯỢC: {total_r:.2f} R\n")

run()
