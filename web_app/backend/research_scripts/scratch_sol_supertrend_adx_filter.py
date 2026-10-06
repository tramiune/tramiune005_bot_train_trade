import sys, os
import pandas as pd
import numpy as np
import time

sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data
import bt_harness as H

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

def get_adx(h, l, c, period=14):
    df = pd.DataFrame({'high': h, 'low': l, 'close': c})
    # pandas_ta is not installed, calculate ADX manually
    tr1 = h - l
    tr2 = np.abs(h - np.roll(c, 1))
    tr3 = np.abs(l - np.roll(c, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]
    
    up = h - np.roll(h, 1)
    down = np.roll(l, 1) - l
    
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    
    atr = np.zeros(len(c))
    p_dm = np.zeros(len(c))
    m_dm = np.zeros(len(c))
    
    # Simple Wilder's Smoothing
    atr[0] = tr[0]
    p_dm[0] = plus_dm[0]
    m_dm[0] = minus_dm[0]
    
    for i in range(1, len(c)):
        atr[i] = atr[i-1] - (atr[i-1]/period) + tr[i]
        p_dm[i] = p_dm[i-1] - (p_dm[i-1]/period) + plus_dm[i]
        m_dm[i] = m_dm[i-1] - (m_dm[i-1]/period) + minus_dm[i]
        
    plus_di = 100 * p_dm / np.where(atr == 0, 1, atr)
    minus_di = 100 * m_dm / np.where(atr == 0, 1, atr)
    
    dx = 100 * np.abs(plus_di - minus_di) / np.where((plus_di + minus_di) == 0, 1, (plus_di + minus_di))
    adx = np.zeros(len(c))
    adx[0] = dx[0]
    for i in range(1, len(c)):
        adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period
        
    return adx

def run():
    print("Loading SOLUSDT 1m data...")
    d1 = bt_data.load("SOLUSDT", "1m")
    sim = H.Sim(d1)
    B = H.resample(d1, 240) # 4H
    c = B["close"].to_numpy()
    h = B["high"].to_numpy()
    l = B["low"].to_numpy()
    ct = B["close_time"].to_numpy()
    
    # Vua Supertrend
    length = 17
    mult = 4.4
    trend, final_ub, final_lb = supertrend_with_bands(h, l, c, length, mult)
    
    cost = 0.12
    adx_thresholds = [0, 15, 20, 25, 30] # 0 = Không dùng ADX (Nguyên bản)
    adx_val = get_adx(h, l, c, 14)
    
    print("Bắt đầu thử nghiệm Bộ Lọc Động Lượng (ADX) để lọc Sideways...\n")
    
    for adx_t in adx_thresholds:
        side = np.zeros(len(B), dtype=int)
        for i in range(1, len(trend)):
            if trend[i] == 1 and trend[i-1] == -1: 
                if adx_val[i-1] > adx_t: side[i] = 1 # Long
            elif trend[i] == -1 and trend[i-1] == 1: 
                if adx_val[i-1] > adx_t: side[i] = -1 # Short
                
        idx = np.nonzero(side)[0]
        trades, pos, e = [], 0, 0.0
        initial_sl_val = 0.0
        
        # Exit logic: We still exit when trend flips, regardless of ADX.
        # But we only ENTER if ADX > threshold.
        # This means we are NOT "always in". We exit and go to cash.
        
        # Wait, if we use ADX filter, the side array only has 1 or -1 at entries.
        # Let's rebuild a "position" array over time
        current_pos = 0
        trade_entry_idx = -1
        
        for i in range(1, len(B)):
            # Tín hiệu vào lệnh
            if current_pos == 0:
                if side[i] == 1: current_pos = 1; trade_entry_idx = i
                elif side[i] == -1: current_pos = -1; trade_entry_idx = i
            
            # Tín hiệu đóng lệnh (Gãy trend)
            if current_pos == 1 and trend[i] == -1:
                # Đóng lệnh
                e_px = sim.o[np.searchsorted(sim.t, ct[trade_entry_idx])]
                ex_px = sim.o[np.searchsorted(sim.t, ct[i])]
                pnl = (ex_px / e_px - 1) * 100 - cost
                sl = (e_px - final_lb[trade_entry_idx-1]) / e_px * 100
                trades.append({'pnl': pnl, 'true_r': pnl / sl if sl > 0 else pnl})
                current_pos = 0
                
            elif current_pos == -1 and trend[i] == 1:
                e_px = sim.o[np.searchsorted(sim.t, ct[trade_entry_idx])]
                ex_px = sim.o[np.searchsorted(sim.t, ct[i])]
                pnl = -1 * (ex_px / e_px - 1) * 100 - cost
                sl = (final_ub[trade_entry_idx-1] - e_px) / e_px * 100
                trades.append({'pnl': pnl, 'true_r': pnl / sl if sl > 0 else pnl})
                current_pos = 0
                
        if len(trades) < 5: continue
        
        T = pd.DataFrame(trades)
        wins = len(T[T['pnl'] > 0])
        wr = wins / len(T) * 100
        total_pnl = T['pnl'].sum()
        total_true_r = T['true_r'].sum()
        
        if adx_t == 0:
            print(f"[NGUYÊN BẢN (KHÔNG LỌC)] ADX > 0:")
        else:
            print(f"[ĐÃ LỌC SIDEWAYS] Bộ lọc ADX > {adx_t}:")
            
        print(f"   - Số Lệnh: {len(T)}")
        print(f"   - Win Rate: {wr:.2f}%")
        print(f"   - Tổng Tiền Tươi %: +{total_pnl:.2f}%")
        print(f"   - Tổng Lợi Nhuận Kép (TRUE R): +{total_true_r:.2f} R\n")

run()
