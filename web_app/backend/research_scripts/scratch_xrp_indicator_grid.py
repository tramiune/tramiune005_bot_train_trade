import itertools
import os
import sys
import numpy as np
import pandas as pd
import time

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
import xrp_nada as X

def run():
    print("Loading XRPUSDT 1m data...")
    d1 = bt_data.load("XRPUSDT", "1m")
    sim = H.Sim(d1)
    
    print("Loading BTCUSDT 1m data...")
    btc1 = bt_data.load("BTCUSDT", "1m")
    
    print("Resampling to 5m...")
    B = H.resample(d1, 5)
    B_btc = H.resample(btc1, 5)
    
    # Merge BTC close
    B_btc_df = pd.DataFrame({'close_time': B_btc['close_time'], 'btc_close': B_btc['close']})
    B_df = pd.DataFrame({'close_time': B['close_time'], 'close': B['close'], 'high': B['high'], 'low': B['low']})
    B_merged = pd.merge(B_df, B_btc_df, on='close_time', how='left').ffill()
    
    c = B["close"].to_numpy()
    cost = 2 * (0.0005 + 0.0001) * 100
    
    print("Calculating Macro Indicators...")
    # 1. XRP EMA 200
    xrp_ema = B_merged['close'].ewm(span=200, adjust=False).mean().values
    f_xrp_uptrend = c > xrp_ema
    
    # 2. BTC EMA 200
    btc_ema = B_merged['btc_close'].ewm(span=200, adjust=False).mean().values
    f_btc_uptrend = B_merged['btc_close'].values > btc_ema
    
    # 3. Session Filter (London/US 08:00 - 20:00 UTC)
    hours = pd.to_datetime(B_merged['close_time'], unit='s').dt.hour.values
    f_session = (hours >= 8) & (hours <= 20)
    
    # Core Entry
    r_os, v_mult, m = 20, 2.5, 3.0
    core_side = X.signals(B, h=8.0, mult=m, rsi_os=r_os, rsi_ob=100-r_os, vol_mult=v_mult)
    
    # Exit Grid
    SL_LIST = [0.75, 1.0]
    RR_LIST = [10, 15, 20]
    
    # Filter combinations
    FILTER_COMBOS = list(itertools.product([False, True], repeat=3))
    
    print(f"Bắt đầu Quét Đa Chiều kết hợp Bộ Lọc Vĩ Mô (EMA, BTC, Session)...")
    
    start_time = time.time()
    rows = []
    
    for use_xrp_ema, use_btc_ema, use_session in FILTER_COMBOS:
        side = core_side.copy()
        
        # Áp dụng bộ lọc
        if use_xrp_ema: side = np.where(f_xrp_uptrend, side, 0)
        if use_btc_ema: side = np.where(f_btc_uptrend, side, 0)
        if use_session: side = np.where(f_session, side, 0)
        
        if (side == 1).sum() < 10:
            continue
            
        for sl, rr in itertools.product(SL_LIST, RR_LIST):
            tp = sl * rr
            T = sim.run(B, side, c * sl / 100, c * tp / 100)
            
            if len(T) < 10:
                continue
                
            wins = int((T.reason == "TP").sum())
            losses = len(T) - wins
            wr = (wins / len(T)) * 100
            
            win_pct = tp - cost
            loss_pct = -sl - cost
            sum_pct = (wins * win_pct) + (losses * loss_pct)
            sum_R = sum_pct / sl
            
            ev_R = sum_R / len(T) if len(T) > 0 else 0
            
            rows.append({
                "XRP_EMA": use_xrp_ema, "BTC_EMA": use_btc_ema, "Session": use_session,
                "SL%": sl, "TP%": tp, "RR": rr,
                "Trades": len(T), "Wins": wins, "WinRate": wr, "Net_R": sum_R, "EV_R": ev_R
            })
            
    end_time = time.time()
    print(f"\nHoàn thành quét trong {end_time - start_time:.1f} giây!")
    
    R_df = pd.DataFrame(rows)
    if len(R_df) > 0:
        R_df = R_df.sort_values("Net_R", ascending=False).head(15)
        print("\n=== TOP 15 CẤU HÌNH BỘ LỌC CHỈ BÁO LÃI NHẤT ===")
        print(R_df.round(2).to_string(index=False))
        
        out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/xrp_indicator_grid.md'
        md = f"# SIÊU QUÉT BỘ LỌC VĨ MÔ (MACRO INDICATORS) CHO XRP 5M\n\n"
        md += "Bảng này kết hợp lõi Nadaraya-Watson (RSI 20, Vol 2.5x) với các chỉ báo Vĩ mô như xu hướng BTC, xu hướng EMA 200 và Phiên giao dịch.\n\n"
        md += "| XRP > EMA200 | BTC > EMA200 | Phiên Âu/Mỹ | SL (%) | TP (%) | 1 Ăn (RR) | Số Lệnh | Win Rate | Lãi Ròng (R) | Lợi thế/Lệnh (EV) |\n"
        md += "|---|---|---|---|---|---|---|---|---|---|\n"
        for i, (_, row) in enumerate(R_df.iterrows()):
            md += f"| {'Có' if row['XRP_EMA'] else 'Không'} | {'Có' if row['BTC_EMA'] else 'Không'} | {'Có' if row['Session'] else 'Không'} | {row['SL%']}% | {row['TP%']}% | 1 ăn {int(row['RR'])} | {int(row['Trades'])} | {row['WinRate']:.1f}% | **+{row['Net_R']:.1f} R** | +{row['EV_R']:.2f} R |\n"
        with open(out_path, 'w') as f:
            f.write(md)
    else:
        print("Không tìm thấy cấu hình nào.")

run()
