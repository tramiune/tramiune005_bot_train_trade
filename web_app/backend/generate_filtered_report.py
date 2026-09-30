import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt
import sys

async def fetch_data(symbol, tf='5m', years=4):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = years * 365 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    
    print(f"Fetching {years} Year(s) of {symbol} {tf} Data (~4 mins)...")
    count = 0
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, tf, since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + 300000
            count += 1
            if count % 20 == 0:
                print(f"[{symbol}] Fetched {len(all_klines)} candles...")
                sys.stdout.flush()
        except Exception:
            await asyncio.sleep(0.5)
    await exchange.close()
    return all_klines

def calculate_daily_vwap(df):
    df['date'] = df['datetime'].dt.date
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['vol_tp'] = df['volume'] * df['tp']
    df['cum_vol'] = df.groupby('date')['volume'].cumsum()
    df['cum_vol_tp'] = df.groupby('date')['vol_tp'].cumsum()
    df['vwap'] = df['cum_vol_tp'] / df['cum_vol']
    df['dev_sq'] = df['volume'] * ((df['tp'] - df['vwap']) ** 2)
    df['cum_dev_sq'] = df.groupby('date')['dev_sq'].cumsum()
    df['variance'] = df['cum_dev_sq'] / df['cum_vol']
    df['sd'] = np.sqrt(df['variance'])
    df['upper_2_5'] = df['vwap'] + (2.5 * df['sd'])
    df['lower_2_5'] = df['vwap'] - (2.5 * df['sd'])
    return df

async def run():
    data = await fetch_data('ETH/USDT', '5m', 4)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    print("Calculating VWAP...")
    df = calculate_daily_vwap(df)
    
    df['bandwidth'] = (df['upper_2_5'] - df['lower_2_5']) / df['vwap'] * 100
    
    # Pre-calculate signals with Bandwidth < 5.0%
    cond_bw = df['bandwidth'] < 5.0
    df['long_signal'] = cond_bw & (df['datetime'].dt.hour > 0) & (df['low'] <= df['lower_2_5']) & (df['close'] > df['lower_2_5']) & (df['close'] > df['open'])
    df['short_signal'] = cond_bw & (df['datetime'].dt.hour > 0) & (df['high'] >= df['upper_2_5']) & (df['close'] < df['upper_2_5']) & (df['close'] < df['open'])
    
    tp_pct = 2.5
    sl_pct = 3.0
    win_profit = 2.50 - 0.04  # $2.46
    loss_profit = -3.00 - 0.04 # -$3.04
    
    trades = []
    print("Simulating trades...")
    i = 1
    while i < len(df) - 1:
        if df['long_signal'].iloc[i] or df['short_signal'].iloc[i]:
            side = 'LONG' if df['long_signal'].iloc[i] else 'SHORT'
            entry_price = df['close'].iloc[i]
            
            if side == 'LONG':
                sl_price = entry_price * (1 - sl_pct/100)
                tp_price = entry_price * (1 + tp_pct/100)
            else:
                sl_price = entry_price * (1 + sl_pct/100)
                tp_price = entry_price * (1 - tp_pct/100)
                
            is_win = False
            exit_idx = i
            for j in range(i+1, min(i+288, len(df))):
                if side == 'LONG':
                    if df['low'].iloc[j] <= sl_price:
                        is_win = False; exit_idx = j; break
                    elif df['high'].iloc[j] >= tp_price:
                        is_win = True; exit_idx = j; break
                else:
                    if df['high'].iloc[j] >= sl_price:
                        is_win = False; exit_idx = j; break
                    elif df['low'].iloc[j] <= tp_price:
                        is_win = True; exit_idx = j; break
            
            if exit_idx > i:
                dt = df['datetime'].iloc[i]
                trades.append({
                    "month": dt.strftime('%Y-%m'),
                    "is_win": is_win
                })
                i = exit_idx
            else:
                i += 1
            continue
        i += 1
            
    res_df = pd.DataFrame(trades)
    
    md_lines = [
        "# Báo Cáo ETH 5m VWAP (Tối Ưu: Băng thông < 5.0%)",
        "",
        "**Thiết lập Cố định (Fixed Size):**",
        "- Vị thế mỗi lệnh: **$100 (Đòn bẩy x1)**",
        "- TP 2.5%: Lãi **+$2.46** (Đã trừ phí $0.04)",
        "- SL 3.0%: Lỗ **-$3.04** (Đã cộng phí $0.04)",
        "- **Bộ lọc thêm: CẤM VÀO LỆNH khi Bandwidth mở rộng trên 5.0%**",
        "",
        "| Tháng | Số Lệnh | Win | Loss | Win Rate | Tổng Lãi/Lỗ (USD) |",
        "|-------|---------|-----|------|----------|-------------------|"
    ]
    
    total_trades = 0
    total_wins = 0
    total_losses = 0
    total_usd = 0.0
    
    for month in sorted(res_df['month'].unique()):
        m_df = res_df[res_df['month'] == month]
        wins = len(m_df[m_df['is_win'] == True])
        losses = len(m_df) - wins
        trades_count = wins + losses
        
        total_trades += trades_count
        total_wins += wins
        total_losses += losses
        
        wr = (wins / trades_count) * 100 if trades_count > 0 else 0
        usd_pnl = (wins * win_profit) + (losses * loss_profit)
        total_usd += usd_pnl
        
        sign = "+" if usd_pnl > 0 else ""
        md_lines.append(f"| {month} | {trades_count} | {wins} | {losses} | {wr:.1f}% | **{sign}{usd_pnl:.2f} $** |")

    md_lines.extend([
        "",
        "### 📊 TỔNG KẾT 4 NĂM",
        f"- **Tổng số lệnh:** {total_trades}",
        f"- **Tổng Thắng / Thua:** {total_wins} Wins / {total_losses} Losses",
        f"- **Win Rate Tổng:** {(total_wins/total_trades)*100:.2f}%",
        f"- **Lợi nhuận ròng 4 năm:** **+{total_usd:.2f} USD**"
    ])

    with open('/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/eth_vwap_optimized_monthly.md', 'w') as f:
        f.write('\n'.join(md_lines))

    print("Markdown artifact generated.")

asyncio.run(run())
