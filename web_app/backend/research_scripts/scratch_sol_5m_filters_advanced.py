import asyncio
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    print("Loading DOGE 1m data...")
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    
    B = df.resample('5min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c, h, l, v = B["close"], B["high"], B["low"], B["volume"]
    
    h_c = h - c.shift()
    l_c = l - c.shift()
    tr = pd.concat([h - l, h_c.abs(), l_c.abs()], axis=1).max(axis=1)
    
    a = tr.rolling(20).mean()
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std()
    
    # 1. Tính Trạng thái Squeeze (Nén)
    on = (mid + 2 * sd < mid + 1.5 * a) & (mid - 2 * sd > mid - 1.5 * a)
    dur = on.groupby((~on).cumsum()).cumsum()
    
    # 2. Tính Cầu dao xu hướng vĩ mô (EMA 1 Ngày trên khung 5m = 24*12 = 288)
    ema_1d = c.ewm(span=288, adjust=False).mean()
    
    bull = c > mid
    
    # Tín hiệu CƠ BẢN (Nén 5 nến, Vol > 1.5x)
    fire_base = (~on) & on.shift(1, fill_value=False) & (dur.shift(1) >= 5) & (v > 1.5 * v.rolling(20).mean())
    sig_base = np.where(fire_base, np.where(bull, 1, -1), 0)
    
    # Tín hiệu LỌC XU HƯỚNG MẸ (Chỉ đánh Long khi trên EMA 1D, Short khi dưới EMA 1D)
    sig_trend = np.copy(sig_base)
    sig_trend = np.where((sig_trend == 1) & (c < ema_1d), 0, sig_trend) # Bỏ Long sai trend
    sig_trend = np.where((sig_trend == -1) & (c > ema_1d), 0, sig_trend) # Bỏ Short sai trend
    
    # Tín hiệu LỌC THỜI GIAN NÉN LÂU HƠN (dur >= 24 nến = 2 tiếng nén)
    fire_time = (~on) & on.shift(1, fill_value=False) & (dur.shift(1) >= 24) & (v > 1.5 * v.rolling(20).mean())
    sig_time = np.where(fire_time, np.where(bull, 1, -1), 0)
    
    # Tín hiệu LỌC KÉP (Trend + Nén lâu)
    sig_combo = np.copy(sig_time)
    sig_combo = np.where((sig_combo == 1) & (c < ema_1d), 0, sig_combo)
    sig_combo = np.where((sig_combo == -1) & (c > ema_1d), 0, sig_combo)
    
    opens = B["open"].values
    highs = B["high"].values
    lows = B["low"].values
    
    tp_pct = 8.0
    sl_pct = 8.0
    fee = 0.05 / 100
    
    def backtest(signals):
        trades = []
        in_pos = False
        tp_price = 0; sl_price = 0; side = 0
        for i in range(288, len(B)-1):
            if not in_pos:
                if signals[i] != 0:
                    in_pos = True
                    side = signals[i]
                    entry_p = opens[i+1]
                    if side == 1:
                        tp_price = entry_p * (1 + tp_pct/100)
                        sl_price = entry_p * (1 - sl_pct/100)
                    else:
                        tp_price = entry_p * (1 - tp_pct/100)
                        sl_price = entry_p * (1 + sl_pct/100)
            else:
                if side == 1:
                    if lows[i] <= sl_price:
                        trades.append(-sl_pct - fee*200)
                        in_pos = False
                    elif highs[i] >= tp_price:
                        trades.append(tp_pct - fee*200)
                        in_pos = False
                else:
                    if highs[i] >= sl_price:
                        trades.append(-sl_pct - fee*200)
                        in_pos = False
                    elif lows[i] <= tp_price:
                        trades.append(tp_pct - fee*200)
                        in_pos = False
        return np.array(trades)

    tr_base = backtest(sig_base)
    tr_trend = backtest(sig_trend)
    tr_time = backtest(sig_time)
    tr_combo = backtest(sig_combo)
    
    def print_stats(name, tr):
        if len(tr) == 0:
            print(f"{name:30s} | Không có lệnh")
            return
        wr = (tr>0).mean()*100
        print(f"{name:30s} | Lệnh: {len(tr):3d} | Win Rate: {wr:5.1f}% | PnL Ròng: {tr.sum():6.2f}%")

    print("\n=== THỬ NGHIỆM ĐA BỘ LỌC ĐỂ CỨU WIN RATE (TP 8, SL 8) ===")
    print_stats("1. Bản Gốc (No Filter)", tr_base)
    print_stats("2. Lọc Xu Hướng (EMA 1 Ngày)", tr_trend)
    print_stats("3. Lọc Lò Xo Nén (>2 tiếng)", tr_time)
    print_stats("4. Hợp Thể (Trend + Lò Xo)", tr_combo)

run()
