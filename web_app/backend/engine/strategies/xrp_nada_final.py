import pandas as pd
import numpy as np

def pine_rsi(src: pd.Series, n: int) -> pd.Series:
    d = np.diff(src, prepend=np.nan)
    up, dn = np.clip(d, 0, None), np.clip(-d, 0, None)
    out = np.full(len(src), np.nan)
    if len(src) <= n: return pd.Series(out)
    au, ad = np.nanmean(up[1:n + 1]), np.nanmean(dn[1:n + 1])
    out[n] = 100 if ad == 0 else 100 - 100 / (1 + au / ad)
    for i in range(n + 1, len(src)):
        au = (au * (n - 1) + up[i]) / n
        ad = (ad * (n - 1) + dn[i]) / n
        out[i] = 100 if ad == 0 else 100 - 100 / (1 + au / ad)
    return pd.Series(out)

def check_xrp_signal(df: pd.DataFrame, return_details: bool = False):
    """
    XRP FINAL KING (Mean Reversion)
    Nadaraya-Watson (h=8.0, mult=3.0) + RSI < 20 / > 80 + Vol < 2.4x
    Requires at least 1000 candles (recommend 1500) to warm up 499-period MAE
    """
    if len(df) < 1000:
        return ("NONE", {}) if return_details else "NONE"
    
    h_bw = 8.0
    mult = 3.0
    rsi_os = 20
    rsi_ob = 80
    vol_mult = 2.4
    
    c = df['close'].to_numpy()
    v = df['volume'].to_numpy()
    
    # Nadaraya-Watson causal kernel
    w = np.exp(-(np.arange(500) ** 2) / (h_bw * h_bw * 2))
    out = np.convolve(c, w)[: len(c)] / w.sum()
    out[:499] = np.nan
    mae = pd.Series(np.abs(c - out)).rolling(499).mean().to_numpy() * mult
    upper = out + mae
    lower = out - mae
    
    # RSI (Pine Script exact implementation)
    r = pine_rsi(df['close'], 14).to_numpy()
    
    # Vol Filter (Volume < SMA20 * 2.4)
    vol_sma = pd.Series(v).rolling(20).mean().to_numpy()
    high_vol = v > vol_sma * vol_mult
    vol_ratio = v / np.where(vol_sma == 0, 1, vol_sma)
    
    i = len(df) - 2 # Latest closed candle
    
    details = {
        'close': float(c[i]) if not np.isnan(c[i]) else 0.0,
        'lower': float(lower[i]) if not np.isnan(lower[i]) else 0.0,
        'upper': float(upper[i]) if not np.isnan(upper[i]) else 0.0,
        'rsi': float(r[i]) if not np.isnan(r[i]) else 0.0,
        'vol_ratio': float(vol_ratio[i]) if not np.isnan(vol_ratio[i]) else 0.0,
    }
    
    if np.isnan(lower[i]) or np.isnan(upper[i]) or np.isnan(r[i]):
        return ("NONE", details) if return_details else "NONE"
        
    cross_dn = (c[i] < lower[i]) and (c[i-1] >= lower[i-1])
    cross_up = (c[i] > upper[i]) and (c[i-1] <= upper[i-1])
    
    signal = "NONE"
    if cross_dn and (r[i] < rsi_os) and not high_vol[i]:
        signal = "LONG"
    elif cross_up and (r[i] > rsi_ob) and not high_vol[i]:
        signal = "SHORT"
        
    return (signal, details) if return_details else signal

