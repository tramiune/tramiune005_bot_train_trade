import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    print("Loading DOGE 1m data...")
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    
    print("Resampling to 15m...")
    B = df.resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c = B["close"].values
    h = B["high"].values
    l = B["low"].values
    v = B["volume"].values
    dts = B.index
    
    # Tính Bollinger Bands & Keltner Channel (Squeeze)
    period = 20
    df_b = pd.DataFrame({'c': c, 'h': h, 'l': l})
    df_b['tr'] = np.maximum(h - l, np.maximum(abs(h - df_b['c'].shift()), abs(l - df_b['c'].shift())))
    df_b['atr'] = df_b['tr'].rolling(period).mean()
    
    df_b['mid'] = df_b['c'].rolling(period).mean()
    df_b['std'] = df_b['c'].rolling(period).std()
    
    bb_up = df_b['mid'] + (2.0 * df_b['std'])
    bb_dn = df_b['mid'] - (2.0 * df_b['std'])
    kc_up = df_b['mid'] + (1.5 * df_b['atr'])
    kc_dn = df_b['mid'] - (1.5 * df_b['atr'])
    
    squeeze_on = (bb_up < kc_up) & (bb_dn > kc_dn)
    sq_dur = squeeze_on.groupby((~squeeze_on).cumsum()).cumsum().values
    
    v_ma = pd.Series(v).rolling(period).mean().values
    
    trades = []
    in_pos = False
    tp_price = 0; sl_price = 0; entry_time = None
    side = 0
    
    # RR 12: SL 1%, TP 12%
    tp_pct = 12.0
    sl_pct = 1.0
    
    print("Đang săn Squeeze Breakout (RR 1:12)...")
    for i in range(200, len(B)-1):
        if not in_pos:
            # Nếu vừa thoát khỏi trạng thái Squeeze (Nén chặt)
            if sq_dur[i-1] >= 10 and not squeeze_on[i]:
                # Breakout lên với Volume to
                if c[i] > bb_up[i] and v[i] > 2.0 * v_ma[i]:
                    in_pos = True
                    side = 1
                    entry_p = c[i]
                    entry_time = dts[i]
                    tp_price = entry_p * (1 + tp_pct/100)
                    sl_price = entry_p * (1 - sl_pct/100)
                
                # Breakout xuống với Volume to
                elif c[i] < bb_dn[i] and v[i] > 2.0 * v_ma[i]:
                    in_pos = True
                    side = -1
                    entry_p = c[i]
                    entry_time = dts[i]
                    tp_price = entry_p * (1 - tp_pct/100)
                    sl_price = entry_p * (1 + sl_pct/100)
        else:
            if side == 1:
                if l[i] <= sl_price:
                    trades.append({'Vào Lệnh': entry_time, 'Chốt Lệnh': dts[i], 'Lãi/Lỗ': -1})
                    in_pos = False
                elif h[i] >= tp_price:
                    trades.append({'Vào Lệnh': entry_time, 'Chốt Lệnh': dts[i], 'Lãi/Lỗ': 12})
                    in_pos = False
            else:
                if h[i] >= sl_price:
                    trades.append({'Vào Lệnh': entry_time, 'Chốt Lệnh': dts[i], 'Lãi/Lỗ': -1})
                    in_pos = False
                elif l[i] <= tp_price:
                    trades.append({'Vào Lệnh': entry_time, 'Chốt Lệnh': dts[i], 'Lãi/Lỗ': 12})
                    in_pos = False

    df_res = pd.DataFrame(trades)
    
    if len(df_res) == 0:
        print("Không có lệnh nào!")
        return
        
    wins = len(df_res[df_res['Lãi/Lỗ'] > 0])
    losses = len(df_res[df_res['Lãi/Lỗ'] <= 0])
    
    print("\n" + "="*60)
    print("🚀 CHIẾN LƯỢC MỚI: DOGE SQUEEZE BREAKOUT (RR 1 ĂN 12)")
    print("="*60)
    print(f"Tổng Lệnh (4 Năm): {len(df_res)} lệnh")
    print(f"Lệnh Thắng: {wins} | Lệnh Thua: {losses}")
    print(f"Win Rate: {wins/len(df_res)*100:.1f}%")
    print(f"Lợi nhuận ròng: +{df_res['Lãi/Lỗ'].sum()} R")

run()
