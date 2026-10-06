import pandas as pd
import numpy as np

def check_sol_signal(df: pd.DataFrame) -> str:
    """
    SOL CƯỠI SÓNG FINAL (Trend Following)
    Supertrend (17, 4.4)
    Returns: "LONG" or "SHORT" or "NONE"
    """
    if len(df) < 50: return "NONE"
    
    period = 17
    mult = 4.4
    
    h = df['high'].to_numpy()
    l = df['low'].to_numpy()
    c = df['close'].to_numpy()
    
    tr1 = h - l
    tr2 = np.abs(h - np.roll(c, 1))
    tr3 = np.abs(l - np.roll(c, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]
    
    atr = np.zeros(len(c))
    atr[0] = tr[0]
    for i in range(1, len(c)): 
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
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
        
    i = len(df) - 2
    
    if trend[i] == 1 and trend[i-1] == -1:
        return "LONG"
    elif trend[i] == -1 and trend[i-1] == 1:
        return "SHORT"
        
    return "NONE"

def get_sol_sl_prices(df: pd.DataFrame):
    # Same calculation to return exact lb/ub for dynamic size calculation
    period, mult = 17, 4.4
    h, l, c = df['high'].to_numpy(), df['low'].to_numpy(), df['close'].to_numpy()
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
    final_ub, final_lb = np.zeros(len(c)), np.zeros(len(c))
    for i in range(1, len(c)):
        if basic_ub[i] < final_ub[i-1] or c[i-1] > final_ub[i-1]: final_ub[i] = basic_ub[i]
        else: final_ub[i] = final_ub[i-1]
        if basic_lb[i] > final_lb[i-1] or c[i-1] < final_lb[i-1]: final_lb[i] = basic_lb[i]
        else: final_lb[i] = final_lb[i-1]
    
    i = len(df) - 2
    return final_lb[i], final_ub[i]
