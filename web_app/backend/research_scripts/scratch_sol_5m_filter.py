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
    
    # --- TÍNH ADX 1 GIỜ ĐỂ LÀM BỘ LỌC REGIME ---
    B_1h = df.resample('1h').agg({'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    length = 14
    tr1 = B_1h['high'] - B_1h['low']
    tr2 = (B_1h['high'] - B_1h['close'].shift(1)).abs()
    tr3 = (B_1h['low'] - B_1h['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    up = B_1h['high'] - B_1h['high'].shift(1)
    down = B_1h['low'].shift(1) - B_1h['low']
    pos_dm = np.where((up > down) & (up > 0), up, 0)
    neg_dm = np.where((down > up) & (down > 0), down, 0)
    
    tr_smooth = tr.ewm(alpha=1/length, adjust=False).mean()
    pos_dm_smooth = pd.Series(pos_dm).ewm(alpha=1/length, adjust=False).mean()
    neg_dm_smooth = pd.Series(neg_dm).ewm(alpha=1/length, adjust=False).mean()
    
    plus_di = 100 * (pos_dm_smooth / tr_smooth)
    minus_di = 100 * (neg_dm_smooth / tr_smooth)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_1h = dx.ewm(alpha=1/length, adjust=False).mean()
    
    # Ghép ADX 1h vào B (5m) theo phương pháp bfill/ffill
    B['adx_1h'] = adx_1h
    B['adx_1h'] = B['adx_1h'].ffill()
    
    c, h, l, v = B["close"], B["high"], B["low"], B["volume"]
    adx = B["adx_1h"].values
    
    h_c = h - c.shift()
    l_c = l - c.shift()
    tr_5m = pd.concat([h - l, h_c.abs(), l_c.abs()], axis=1).max(axis=1)
    
    a = tr_5m.rolling(20).mean()
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std()
    
    on = (mid + 2 * sd < mid + 1.5 * a) & (mid - 2 * sd > mid - 1.5 * a)
    dur = on.groupby((~on).cumsum()).cumsum()
    fire = (~on) & on.shift(1, fill_value=False) & (dur.shift(1) >= 5) 
    bull = c > mid
    
    # 3 LOẠI TÍN HIỆU TỪ LỎNG TỚI CHẶT
    sig_goc = np.where(fire & (v > 1.5 * v.rolling(20).mean()), np.where(bull, 1, -1), 0)
    sig_vol = np.where(fire & (v > 3.0 * v.rolling(20).mean()), np.where(bull, 1, -1), 0)
    sig_adx = np.where(fire & (v > 1.5 * v.rolling(20).mean()) & (adx > 25), np.where(bull, 1, -1), 0)
    
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
        for i in range(20, len(B)-1):
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

    tr_goc = backtest(sig_goc)
    tr_vol = backtest(sig_vol)
    tr_adx = backtest(sig_adx)
    
    def print_stats(name, tr):
        if len(tr) == 0:
            print(f"{name:25s} | Không có lệnh nào")
            return
        wr = (tr>0).mean()*100
        print(f"{name:25s} | Số Lệnh: {len(tr):3d} | Win Rate: {wr:5.1f}% | PnL Ròng: {tr.sum():6.2f}%")

    print("\n=== THÍ NGHIỆM: CỐ GẮNG LỌC LỆNH THUA (TP 8, SL 8) ===")
    print_stats("Bản Gốc (Vol > 1.5x)", tr_goc)
    print_stats("Siêu Khối Lượng (Vol > 3x)", tr_vol)
    print_stats("Lọc Vĩ Mô (ADX 1h > 25)", tr_adx)

run()
