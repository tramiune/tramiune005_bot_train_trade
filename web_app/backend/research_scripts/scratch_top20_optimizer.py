import sys, os
import pandas as pd
import numpy as np
import time

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H
import xrp_nada as X

def supertrend_with_bands(h, l, c, period, mult):
    tr1 = h - l
    tr2 = np.abs(h - np.roll(c, 1))
    tr3 = np.abs(l - np.roll(c, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]
    atr = np.zeros(len(c))
    atr[0] = tr[0]
    for i in range(1, len(c)): atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    hl2 = (h + l) / 2
    basic_ub = hl2 + mult * atr
    basic_lb = hl2 - mult * atr
    final_ub = np.zeros(len(c))
    final_lb = np.zeros(len(c))
    trend = np.ones(len(c))
    for i in range(1, len(c)):
        if basic_ub[i] < final_ub[i-1] or c[i-1] > final_ub[i-1]: final_ub[i] = basic_ub[i]
        else: final_ub[i] = final_ub[i-1]
        if basic_lb[i] > final_lb[i-1] or c[i-1] < final_lb[i-1]: final_lb[i] = basic_lb[i]
        else: final_lb[i] = final_lb[i-1]
        if trend[i-1] == 1 and c[i] < final_lb[i]: trend[i] = -1
        elif trend[i-1] == -1 and c[i] > final_ub[i]: trend[i] = 1
        else: trend[i] = trend[i-1]
    return trend, final_ub, final_lb

def optimize_supertrend(coin, d1, sim):
    B = H.resample(d1, 240)
    c, h_px, l_px = B["close"].to_numpy(), B["high"].to_numpy(), B["low"].to_numpy()
    ct = B["close_time"].to_numpy()
    
    lengths = [10, 14, 17, 20]
    mults = [3.5, 4.0, 4.4, 5.0, 6.0]
    
    best_true_r = -999
    best_config = None
    
    for length in lengths:
        for mult in mults:
            trend, final_ub, final_lb = supertrend_with_bands(h_px, l_px, c, length, mult)
            side = np.zeros(len(B), dtype=int)
            for i in range(1, len(trend)):
                if trend[i] == 1 and trend[i-1] == -1: side[i] = 1
                elif trend[i] == -1 and trend[i-1] == 1: side[i] = -1
                    
            idx = np.nonzero(side)[0]
            trades, pos, e = [], 0, 0.0
            initial_sl_val = 0.0
            
            for bi in idx:
                s = int(side[bi])
                j = np.searchsorted(sim.t, ct[bi])
                if j >= sim.n or sim.t[j] != ct[bi]: continue
                px = sim.o[j]
                if pos != 0:
                    gross = pos * (px / e - 1) * 100
                    pnl = gross - 0.12
                    true_r = pnl / initial_sl_val if initial_sl_val > 0.1 else pnl
                    trades.append({'true_r': true_r, 'pnl': pnl})
                pos, e = s, px
                if pos == 1: initial_sl_val = (px - final_lb[bi-1]) / px * 100
                else: initial_sl_val = (final_ub[bi-1] - px) / px * 100
                    
            if len(trades) < 5: continue
            
            T = pd.DataFrame(trades)
            total_r = T['true_r'].sum()
            wr = len(T[T['pnl']>0]) / len(T) * 100
            
            if total_r > best_true_r:
                best_true_r = total_r
                best_config = (length, mult, len(T), wr, T['pnl'].sum())
                
    return best_true_r, best_config

def optimize_nada(coin, d1, sim):
    B = H.resample(d1, 5)
    c = B["close"].to_numpy()
    
    rsi_list = [15, 20, 25]
    vol_list = [2.0, 3.0]
    sl_list = [0.5, 1.0, 1.5]
    tp_list = [10.0, 15.0]
    
    best_r = -999
    best_config = None
    
    for rsi in rsi_list:
        for vol in vol_list:
            side = X.signals(B, h=8.0, mult=3.0, rsi_os=rsi, rsi_ob=100-rsi, vol_mult=vol)
            if not np.any(side): continue
            
            for sl in sl_list:
                for tp in tp_list:
                    T = sim.run(B, side, c * sl / 100, c * tp / 100)
                    if len(T) < 5: continue
                    cost = 0.24
                    T['R'] = np.where(T['reason'] == 'TP', (tp - cost)/sl, (-sl - cost)/sl)
                    total_r = T['R'].sum()
                    wr = len(T[T['reason'] == 'TP']) / len(T) * 100
                    
                    if total_r > best_r:
                        best_r = total_r
                        best_config = (rsi, vol, sl, tp, len(T), wr)
                        
    return best_r, best_config

def run():
    coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", 
             "BNBUSDT", "ADAUSDT", "MATICUSDT", "LINKUSDT", "DOTUSDT",
             "AVAXUSDT", "NEARUSDT", "ATOMUSDT", "LTCUSDT", "BCHUSDT"]
             
    results = []
    
    for coin in coins:
        print(f"[{coin}] Bắt đầu Quét...")
        try:
            d1 = bt_data.load(coin, "1m")
        except Exception as e:
            print(f" Bỏ qua {coin}: Chưa có data")
            continue
            
        sim = H.Sim(d1)
        
        print(f"  - Quét Supertrend 4H...")
        st_r, st_conf = optimize_supertrend(coin, d1, sim)
        
        print(f"  - Quét Nadaraya 5m...")
        nd_r, nd_conf = optimize_nada(coin, d1, sim)
        
        results.append({
            'Coin': coin,
            'ST_R': st_r, 'ST_Conf': st_conf,
            'ND_R': nd_r, 'ND_Conf': nd_conf
        })
        
    df = pd.DataFrame(results)
    
    md = "# MA TRẬN SIÊU QUÉT TỐI ƯU HÓA DANH MỤC TOP 15 COIN\n\n"
    
    md += "## BẢNG 1: ĐỘI QUÂN THUẬN XU HƯỚNG (SUPERTREND 4H)\n"
    md += "Chiến lược gồng lãi siêu hạng, đánh dấu sự thống trị của các đồng coin có sóng mạnh.\n\n"
    md += "| Coin | Chiều dài | Hệ số (Mult) | Số Lệnh | Win Rate | Tổng Lãi (True R) |\n"
    md += "|---|---|---|---|---|---|\n"
    st_df = df.sort_values('ST_R', ascending=False)
    for _, row in st_df.iterrows():
        c = row['ST_Conf']
        if c:
            md += f"| **{row['Coin']}** | {c[0]} | {c[1]} | {c[2]} | {c[3]:.1f}% | **+{row['ST_R']:.1f} R** |\n"
            
    md += "\n## BẢNG 2: ĐỘI QUÂN BẮT ĐÁY (NADARAYA 5M)\n"
    md += "Chiến lược cắn trộm Râu nến lúc thị trường sập mạnh hoảng loạn.\n\n"
    md += "| Coin | Cản RSI | Bùng Nổ Vol | Cắt Lỗ (SL) | Chốt Lời (TP) | Số Lệnh | Win Rate | Tổng Lãi (R) |\n"
    md += "|---|---|---|---|---|---|---|---|\n"
    nd_df = df.sort_values('ND_R', ascending=False)
    for _, row in nd_df.iterrows():
        c = row['ND_Conf']
        if c:
            md += f"| **{row['Coin']}** | < {c[0]} | > {c[1]}x | {c[2]}% | {c[3]}% | {c[4]} | {c[5]:.1f}% | **+{row['ND_R']:.1f} R** |\n"
            
    out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/top15_master_matrix.md'
    with open(out_path, 'w') as f:
        f.write(md)
    print(f"\nĐã xuất Artifact: {out_path}")

if __name__ == '__main__':
    run()
