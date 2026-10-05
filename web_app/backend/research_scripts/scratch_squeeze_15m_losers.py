import asyncio
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    B = df.resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    c, h, l, v = B["close"], B["high"], B["low"], B["volume"]
    
    h_c = h - c.shift()
    l_c = l - c.shift()
    tr = pd.concat([h - l, h_c.abs(), l_c.abs()], axis=1).max(axis=1)
    
    a = tr.rolling(20).mean()
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std()
    
    on = (mid + 2 * sd < mid + 1.5 * a) & (mid - 2 * sd > mid - 1.5 * a)
    dur = on.groupby((~on).cumsum()).cumsum()
    fire = (~on) & on.shift(1, fill_value=False) & (dur.shift(1) >= 5) & (v > 1.5 * v.rolling(20).mean())
    bull = c > mid
    
    sig_follow = np.where(fire, np.where(bull, 1, -1), 0)
    
    opens = B["open"].values
    highs = B["high"].values
    lows = B["low"].values
    dts = B.index
    
    tp_pct = 5.0
    sl_pct = 2.0
    
    trades = []
    in_pos = False
    tp_price = 0; sl_price = 0; side = 0; entry_time = None; entry_p = 0
    
    for i in range(20, len(B)-1):
        if not in_pos:
            if sig_follow[i] != 0:
                in_pos = True
                side = sig_follow[i]
                entry_p = opens[i+1]
                entry_time = dts[i+1]
                if side == 1:
                    tp_price = entry_p * (1 + tp_pct/100)
                    sl_price = entry_p * (1 - sl_pct/100)
                else:
                    tp_price = entry_p * (1 - tp_pct/100)
                    sl_price = entry_p * (1 + sl_pct/100)
        else:
            if side == 1:
                if lows[i] <= sl_price:
                    trades.append({'time': entry_time, 'side': 'LONG', 'entry': entry_p, 'pnl': -sl_pct, 'exit_time': dts[i]})
                    in_pos = False
                elif highs[i] >= tp_price:
                    trades.append({'time': entry_time, 'side': 'LONG', 'entry': entry_p, 'pnl': tp_pct, 'exit_time': dts[i]})
                    in_pos = False
            else:
                if highs[i] >= sl_price:
                    trades.append({'time': entry_time, 'side': 'SHORT', 'entry': entry_p, 'pnl': -sl_pct, 'exit_time': dts[i]})
                    in_pos = False
                elif lows[i] <= tp_price:
                    trades.append({'time': entry_time, 'side': 'SHORT', 'entry': entry_p, 'pnl': tp_pct, 'exit_time': dts[i]})
                    in_pos = False
                    
    df_trades = pd.DataFrame(trades)
    losers = df_trades[df_trades['pnl'] < 0].copy()
    
    # Lấy ra 5 lệnh thua của Long và 5 lệnh thua của Short trong năm 2025 (Năm thua nhiều nhất)
    losers['year'] = losers['time'].dt.year
    losers_2025 = losers[losers['year'] == 2025]
    
    print("=== DANH SÁCH 10 LỆNH THUA TIÊU BIỂU (NĂM 2025) ĐỂ SẾP LÊN TRADINGVIEW SOI ===")
    print("\n--- 5 LỆNH LONG BỊ CẮN STOPLOSS (-2%) ---")
    long_losers = losers_2025[losers_2025['side'] == 'LONG'].head(5)
    for _, r in long_losers.iterrows():
        print(f"Vào lệnh lúc: {r['time']} | Entry: {r['entry']:.5f} | Bị cắt lỗ lúc: {r['exit_time']}")
        
    print("\n--- 5 LỆNH SHORT BỊ CẮN STOPLOSS (-2%) ---")
    short_losers = losers_2025[losers_2025['side'] == 'SHORT'].head(5)
    for _, r in short_losers.iterrows():
        print(f"Vào lệnh lúc: {r['time']} | Entry: {r['entry']:.5f} | Bị cắt lỗ lúc: {r['exit_time']}")

run()
