import sys, os
import pandas as pd
import numpy as np
import time

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H

def ema(c, period):
    alpha = 2 / (period + 1)
    out = np.zeros_like(c)
    out[0] = c[0]
    for i in range(1, len(c)):
        out[i] = c[i] * alpha + out[i-1] * (1 - alpha)
    return out

def find_fvg_signals_filtered(h, l, c, v, entry_type='edge', rr_ratio=2.0):
    side = np.zeros(len(c), dtype=int)
    limit_px = np.full(len(c), np.nan)
    sl_px = np.full(len(c), np.nan)
    tp_px = np.full(len(c), np.nan)
    
    prev2_h = np.roll(h, 2)
    prev2_l = np.roll(l, 2)
    
    # 1. Bộ lọc Trend: EMA 200
    ema200 = ema(c, 200)
    
    # 2. Bộ lọc Khối lượng Bùng nổ (Displacement Candle)
    vol_ma = pd.Series(v).rolling(20).mean().to_numpy()
    prev_v = np.roll(v, 1) # Nến 2 (Nến tạo gap)
    massive_vol = prev_v > (vol_ma * 2.0) # Khối lượng nến 2 phải gấp đôi trung bình
    
    # Điều kiện FVG cơ bản
    bull_fvg_base = (l > prev2_h) & (c > np.roll(c, 1))
    bear_fvg_base = (h < prev2_l) & (c < np.roll(c, 1))
    
    # Ép bộ lọc vào
    bull_fvg = bull_fvg_base & massive_vol & (c > ema200)
    bear_fvg = bear_fvg_base & massive_vol & (c < ema200)
    
    for i in range(2, len(c)):
        if bull_fvg[i]:
            side[i] = 1
            if entry_type == 'edge': limit_px[i] = prev2_h[i]
            else: limit_px[i] = (prev2_h[i] + l[i]) / 2.0
            
            sl_px[i] = prev2_l[i]
            risk = limit_px[i] - sl_px[i]
            if risk <= 0: side[i] = 0; continue
            tp_px[i] = limit_px[i] + risk * rr_ratio
            
        elif bear_fvg[i]:
            side[i] = -1
            if entry_type == 'edge': limit_px[i] = prev2_l[i]
            else: limit_px[i] = (prev2_l[i] + h[i]) / 2.0
                
            sl_px[i] = prev2_h[i]
            risk = sl_px[i] - limit_px[i]
            if risk <= 0: side[i] = 0; continue
            tp_px[i] = limit_px[i] - risk * rr_ratio
            
    return side, limit_px, tp_px, sl_px

def run():
    print("Loading BTCUSDT 1m data...")
    d1 = bt_data.load("BTCUSDT", "1m")
    sim = H.Sim(d1)
    
    tfs = [15, 60, 240]
    rrs = [1.5, 2.0, 3.0]
    entry_types = ['edge', 'midpoint']
    
    results = []
    print("Bắt đầu Quét lại FVG với BỘ LỌC KÉP (EMA 200 + Bùng nổ Volume)...")
    start_t = time.time()
    
    for tf in tfs:
        B = H.resample(d1, tf)
        c = B["close"].to_numpy()
        h = B["high"].to_numpy()
        l = B["low"].to_numpy()
        v = B["volume"].to_numpy()
        
        valid_min = tf * 10 
        
        for rr in rrs:
            for et in entry_types:
                side, limit_px, tp_px, sl_px = find_fvg_signals_filtered(h, l, c, v, entry_type=et, rr_ratio=rr)
                if not np.any(side): continue
                
                T = sim.run_limit(B, side, limit_px, tp_px, sl_px, valid_min=valid_min, tp_limit=True)
                if len(T) < 5: continue
                
                trades = len(T)
                wins = len(T[T['net'] > 0])
                wr = (wins / trades) * 100 if trades > 0 else 0
                
                fee_penalty = 0.15 # Trừ 0.15 R tiền phí
                
                T['raw_r'] = np.where(T['reason'] == 'TP', rr, -1.0)
                T['net_r'] = T['raw_r'] - fee_penalty
                
                total_r = T['net_r'].sum()
                
                results.append({
                    'Khung': f"{tf}m",
                    'Entry': et,
                    'RR': rr,
                    'Số Lệnh': trades,
                    'WinRate': wr,
                    'Tổng Lãi R': total_r
                })
                
    end_t = time.time()
    print(f"Hoàn thành Quét {len(tfs)*len(rrs)*len(entry_types)} kịch bản đã LỌC trong {end_t - start_t:.1f}s!\n")
    
    df = pd.DataFrame(results)
    if len(df) > 0:
        df = df.sort_values('Tổng Lãi R', ascending=False)
        print("=== BẢNG XẾP HẠNG SMC (FVG) ĐÃ QUA BỘ LỌC KHẮC NGHIỆT ===")
        print(df.head(15).round(2).to_string(index=False))
        
        out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/smc_fvg_filtered_report.md'
        md = "# CHIẾN LƯỢC SMC (FVG) SAU KHI LẮP BỘ LỌC ĐẠI BÁC\n\n"
        md += f"**Điều kiện Lọc Tàn Bạo:**\n1. Giá phải thuận Xu Hướng (Nằm trên/dưới EMA 200).\n2. Cây nến tạo Gap phải có Khối Lượng Bùng Nổ (Volume > 2x Trung bình).\n\n"
        md += "| Khung (Nến) | Vị Trí Lắp Lệnh | Tỷ lệ R:R | Số lệnh Khớp | Win Rate | TỔNG LÃI THỰC NHẬN (R) |\n"
        md += "|---|---|---|---|---|---|\n"
        for i, (_, row) in enumerate(df.head(20).iterrows()):
            md += f"| **{row['Khung']}** | {row['Entry']} | 1 : {row['RR']} | {int(row['Số Lệnh'])} | {row['WinRate']:.1f}% | **{row['Tổng Lãi R']:.2f} R** |\n"
            
        with open(out_path, 'w') as f:
            f.write(md)
    else:
        print("Không có cấu hình nào vượt qua được bộ lọc!")

run()
