import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(".agents/skills/honest-backtest/scripts"))
import bt_data

def run():
    df = bt_data.load("DOGEUSDT", "1m")
    df.set_index(pd.to_datetime(df['time'], unit='s'), inplace=True)
    B = df.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    c, h, l = B["close"].values, B["high"].values, B["low"].values
    opens, dts = B["open"].values, B.index
    
    length = 14
    multiplier = 5.0
    
    tr1 = h - l
    tr2 = np.abs(h - np.roll(c, 1))
    tr3 = np.abs(l - np.roll(c, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = 0
    
    atr = pd.Series(tr).rolling(length).mean().values
    hl2 = (h + l) / 2
    
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    in_uptrend = np.ones(len(B), dtype=bool)
    
    for i in range(1, len(B)):
        if c[i] > upper_band[i-1]:
            in_uptrend[i] = True
        elif c[i] < lower_band[i-1]:
            in_uptrend[i] = False
        else:
            in_uptrend[i] = in_uptrend[i-1]
            if in_uptrend[i] and lower_band[i] < lower_band[i-1]:
                lower_band[i] = lower_band[i-1]
            if not in_uptrend[i] and upper_band[i] > upper_band[i-1]:
                upper_band[i] = upper_band[i-1]
                
    trades = []
    in_pos = False; entry_p = 0; entry_t = None
    
    for i in range(length, len(B)-1):
        if not in_pos:
            if not in_uptrend[i-1] and in_uptrend[i]:
                in_pos = True
                entry_p = opens[i+1]
                entry_t = dts[i+1]
        else:
            if in_uptrend[i-1] and not in_uptrend[i]:
                exit_p = opens[i+1]
                pnl = ((exit_p - entry_p) / entry_p) * 100 - 0.1 # trừ phí 0.1%
                hold_days = (dts[i+1] - entry_t).total_seconds() / 86400
                trades.append({
                    'STT': len(trades) + 1,
                    'Vào Lệnh': entry_t.strftime('%Y-%m-%d %H:%M'),
                    'Giá Mua': f"{entry_p:.5f}",
                    'Chốt Lệnh': dts[i+1].strftime('%Y-%m-%d %H:%M'),
                    'Giá Bán': f"{exit_p:.5f}",
                    'Thời gian Gồng': f"{hold_days:.1f} ngày",
                    'PnL Ròng': pnl
                })
                in_pos = False
                
    df_res = pd.DataFrame(trades)
    
    # Generate Markdown Table
    md_content = "# BÁO CÁO CHI TIẾT 39 LỆNH: SUPERTREND 4H (DOGE)\n\n"
    md_content += "**Cấu hình: Length = 14, Multiplier = 5.0 (Tối ưu hóa lợi nhuận vĩ mô)**\n\n"
    
    wins = df_res[df_res['PnL Ròng'] > 0]
    losses = df_res[df_res['PnL Ròng'] <= 0]
    
    md_content += f"- **Tổng số lệnh:** {len(df_res)}\n"
    md_content += f"- **Lệnh Thắng:** {len(wins)} ({len(wins)/len(df_res)*100:.1f}%)\n"
    md_content += f"- **Lệnh Thua:** {len(losses)} ({len(losses)/len(df_res)*100:.1f}%)\n"
    md_content += f"- **Tổng Lãi Ròng:** +{df_res['PnL Ròng'].sum():.2f}%\n"
    md_content += f"- **Lãi Trung Bình / Lệnh Thắng:** +{wins['PnL Ròng'].mean():.2f}%\n"
    md_content += f"- **Lỗ Trung Bình / Lệnh Thua:** {losses['PnL Ròng'].mean():.2f}%\n\n"
    
    md_content += "| STT | Thời gian Vào Lệnh | Giá Mua | Thời gian Cắt Lệnh | Giá Bán | Thời gian Gồng | Lãi/Lỗ (%) |\n"
    md_content += "|---|---|---|---|---|---|---|\n"
    
    for _, row in df_res.iterrows():
        pnl = row['PnL Ròng']
        pnl_str = f"**<span style='color:green'>+{pnl:.2f}%</span>**" if pnl > 0 else f"<span style='color:red'>{pnl:.2f}%</span>"
        md_content += f"| {row['STT']} | {row['Vào Lệnh']} | {row['Giá Mua']} | {row['Chốt Lệnh']} | {row['Giá Bán']} | {row['Thời gian Gồng']} | {pnl_str} |\n"
        
    with open('/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/supertrend_39_trades.md', 'w') as f:
        f.write(md_content)
        
    print("Đã tạo Artifact: supertrend_39_trades.md")

run()
