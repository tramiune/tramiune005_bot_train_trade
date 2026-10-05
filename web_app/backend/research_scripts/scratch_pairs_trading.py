import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt
import sys

async def fetch_data(symbol, tf='1h', years=4):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = years * 365 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    print(f"Fetching {years} Year(s) of {symbol} {tf} Data...")
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, tf, since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + (60 * 60 * 1000)
        except Exception:
            await asyncio.sleep(0.5)
    await exchange.close()
    return all_klines

async def run():
    print("Downloading BTC and ETH Data...")
    btc_data = await fetch_data('BTC/USDT', '1h', 4)
    eth_data = await fetch_data('ETH/USDT', '1h', 4)
    
    btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    eth_df = pd.DataFrame(eth_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Align Data
    btc_df = btc_df.drop_duplicates(subset=['timestamp']).set_index('timestamp')
    eth_df = eth_df.drop_duplicates(subset=['timestamp']).set_index('timestamp')
    
    df = eth_df[['close']].join(btc_df[['close']], lsuffix='_eth', rsuffix='_btc').dropna()
    df.reset_index(inplace=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    print("Calculating Z-Score Spread...")
    # Ratio ETH / BTC
    df['ratio'] = df['close_eth'] / df['close_btc']
    
    # Rolling Mean & Std of Ratio (Rolling window = 200 hours)
    window = 200
    df['ratio_mean'] = df['ratio'].rolling(window=window).mean()
    df['ratio_std'] = df['ratio'].rolling(window=window).std()
    
    # Calculate Z-Score
    df['z_score'] = (df['ratio'] - df['ratio_mean']) / df['ratio_std']
    
    trades = []
    in_position = False
    current_side = 0 # 1 means LONG ETH/SHORT BTC, -1 means SHORT ETH/LONG BTC
    entry_eth = 0.0
    entry_btc = 0.0
    entry_time = None
    
    fee_rate = 0.04 / 100 # Assuming Maker fee for both legs (Binance Futures is 0.02%)
    # Total fee to open both legs = 2 * 0.02 = 0.04%. Total fee to close = 0.04%. Total = 0.08%.
    
    print("Simulating Pairs Trading...")
    
    for i in range(window, len(df)):
        z = df['z_score'].iloc[i]
        c_eth = df['close_eth'].iloc[i]
        c_btc = df['close_btc'].iloc[i]
        
        if not in_position:
            # Enter when Z-Score is extreme
            if z < -2.0:
                # ETH is undervalued relative to BTC
                # LONG ETH, SHORT BTC
                in_position = True
                current_side = 1
                entry_eth = c_eth
                entry_btc = c_btc
                entry_time = df['datetime'].iloc[i]
            elif z > 2.0:
                # ETH is overvalued relative to BTC
                # SHORT ETH, LONG BTC
                in_position = True
                current_side = -1
                entry_eth = c_eth
                entry_btc = c_btc
                entry_time = df['datetime'].iloc[i]
        else:
            # Exit when Z-Score reverts to 0 (Mean Reversion)
            # Stop Loss (Catastrophic divergence) if Z-Score > 4.0 or < -4.0
            is_exit = False
            is_sl = False
            
            if current_side == 1 and (z >= 0 or z < -4.0):
                is_exit = True
                if z < -4.0: is_sl = True
            elif current_side == -1 and (z <= 0 or z > 4.0):
                is_exit = True
                if z > 4.0: is_sl = True
                
            if is_exit:
                # Calculate PnL for each leg
                if current_side == 1:
                    eth_pnl_pct = (c_eth - entry_eth) / entry_eth
                    btc_pnl_pct = (entry_btc - c_btc) / entry_btc # Short leg
                else:
                    eth_pnl_pct = (entry_eth - c_eth) / entry_eth # Short leg
                    btc_pnl_pct = (c_btc - entry_btc) / entry_btc
                    
                # Net PnL minus fees (2 legs open, 2 legs close -> 4 * fee_rate per leg)
                net_pnl_pct = eth_pnl_pct + btc_pnl_pct - (fee_rate * 4)
                
                trades.append({
                    "entry_time": entry_time,
                    "exit_time": df['datetime'].iloc[i],
                    "side": "LONG ETH / SHORT BTC" if current_side == 1 else "SHORT ETH / LONG BTC",
                    "pnl_pct": net_pnl_pct * 100,
                    "is_sl": is_sl
                })
                
                in_position = False
                current_side = 0

    res_df = pd.DataFrame(trades)
    
    if len(res_df) == 0:
        print("No trades executed.")
        return
        
    wins = res_df[res_df['pnl_pct'] > 0]
    losses = res_df[res_df['pnl_pct'] <= 0]
    
    wr = len(wins) / len(res_df) * 100
    avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
    avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0
    total_pnl = res_df['pnl_pct'].sum()
    
    # Calculate Max Drawdown based on cumulative sum
    cum_pnl = res_df['pnl_pct'].cumsum()
    peak = cum_pnl.cummax()
    drawdown = peak - cum_pnl
    max_dd = drawdown.max()
    
    print("\n" + "="*60)
    print("=== STATISTICAL ARBITRAGE (ETH/BTC Z-SCORE) ===")
    print("Khung: 1H | SMA: 200 | Vào lệnh: Z > 2.0 | Chốt lời: Z = 0")
    print("="*60)
    print(f"Tổng số lệnh: {len(res_df)}")
    print(f"Thắng: {len(wins)} | Thua: {len(losses)} | Win Rate: {wr:.2f}%")
    print(f"Trung bình Lãi: +{avg_win:.2f}% | Trung bình Lỗ: {avg_loss:.2f}%")
    print(f"LỢI NHUẬN RÒNG (Total PnL): +{total_pnl:.2f}%")
    print(f"Sụt giảm tối đa (Max Drawdown): -{max_dd:.2f}%")
    
    # Sharpe Ratio roughly
    std_dev = res_df['pnl_pct'].std()
    if std_dev > 0:
        sharpe = (res_df['pnl_pct'].mean() / std_dev) * np.sqrt(len(res_df))
        print(f"Chỉ số Sharpe Ratio: {sharpe:.2f} (Quỹ thường đòi hỏi > 1.5)")

asyncio.run(run())
