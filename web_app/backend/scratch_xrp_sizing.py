import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt

def calculate_causal_nadaraya_watson(close, h=8, window=100, mult=1.5):
    n = len(close)
    smoothed = np.zeros(n)
    smoothed[:] = np.nan
    i_arr = np.arange(window)
    weights = np.exp(-(i_arr**2) / (2 * h**2))
    sum_weights = np.sum(weights)
    close_vals = close.values
    for t in range(window, n):
        past_closes = close_vals[t-window+1 : t+1][::-1] 
        smoothed[t] = np.sum(past_closes * weights) / sum_weights
    df = pd.DataFrame({'close': close, 'smoothed': smoothed})
    df['mae'] = (df['close'] - df['smoothed']).abs().rolling(window=window).mean()
    df['lower'] = df['smoothed'] - (mult * df['mae'])
    return df['lower']

async def fetch_data(symbol):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = 365 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, '5m', since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + 300000 
        except:
            await asyncio.sleep(0.5)
    await exchange.close()
    return all_klines

async def run():
    xrp_data = await fetch_data('XRP/USDT')
    btc_data = await fetch_data('BTC/USDT')
    
    df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    btc_df = btc_df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df = pd.merge(df, btc_df[['timestamp', 'close']], on='timestamp', how='inner', suffixes=('', '_btc'))
    
    df['nada_low'] = calculate_causal_nadaraya_watson(df['close'], h=8, window=100, mult=1.5)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    df['btc_ema200'] = df['close_btc'].ewm(span=200, adjust=False).mean()
    
    tp_pct = 1.5; sl_pct = 3.0
    rsi_limit = 40; vol_limit = 1.0
    trades = []
    
    i = 500
    while i < len(df) - 1:
        if df['low'].iloc[i] <= df['nada_low'].iloc[i] and df['close'].iloc[i] > df['nada_low'].iloc[i]:
            if df['rsi'].iloc[i] < rsi_limit and df['vol_ratio'].iloc[i] > vol_limit:
                if df['close_btc'].iloc[i] > df['btc_ema200'].iloc[i]:
                    
                    entry_price = df['close'].iloc[i]
                    sl = entry_price * (1 - sl_pct/100)
                    tp = entry_price * (1 + tp_pct/100)
                    
                    is_win = False; exit_idx = i
                    for j in range(i+1, min(i+288, len(df))):
                        if df['low'].iloc[j] <= sl:
                            is_win = False; exit_idx = j; break
                        elif df['high'].iloc[j] >= tp:
                            is_win = True; exit_idx = j; break
                            
                    if exit_idx > i:
                        trades.append({"is_win": is_win})
                        i = exit_idx
                    else:
                        i += 1
                    continue
        i += 1
        
    print("\n=== QUẢN TRỊ VỐN: LÃI KÉP vs CỐ ĐỊNH (1 NĂM) ===")
    
    # 5% Risk per trade.
    # Risk Multiplier = 5% / 3.04% = 1.644x Leverage
    # Win = 1.46% * 1.644 = +2.40% Account gain.
    
    loss_pct = 0.05       # Lỗ 5% tài khoản
    win_pct = 0.024       # Lãi 2.4% tài khoản
    
    # Lãi Kép (Đánh theo % tài khoản HIỆN TẠI)
    balance_comp = 10_000_000
    max_comp = balance_comp; min_comp = balance_comp
    
    # Cố Định (Chỉ dùng đúng 5% của 10 Triệu ban đầu = 500k cho mỗi lệnh mãi mãi)
    balance_fixed = 10_000_000
    win_vnd = 10_000_000 * win_pct
    loss_vnd = 10_000_000 * loss_pct
    max_fixed = balance_fixed; min_fixed = balance_fixed
    
    for t in trades:
        # Kép
        if t["is_win"]:
            balance_comp *= (1 + win_pct)
        else:
            balance_comp *= (1 - loss_pct)
        if balance_comp > max_comp: max_comp = balance_comp
        if balance_comp < min_comp: min_comp = balance_comp
            
        # Cố định
        if t["is_win"]:
            balance_fixed += win_vnd
        else:
            balance_fixed -= loss_vnd
        if balance_fixed > max_fixed: max_fixed = balance_fixed
        if balance_fixed < min_fixed: min_fixed = balance_fixed
            
    print(f"\n1. ĐÁNH LÃI KÉP (Risk 5% số dư hiện tại mỗi lệnh):")
    print(f"- Vốn ban đầu: 10,000,000 VND")
    print(f"- Lãi thu về:  {(balance_comp - 10000000):,.0f} VND (+{((balance_comp/10000000)-1)*100:.1f}%)")
    print(f"- Đỉnh cao:    {max_comp:,.0f} VND")
    print(f"- Đáy sâu:     {min_comp:,.0f} VND")

    print(f"\n2. ĐÁNH CỐ ĐỊNH (Chịu rủi ro cố định 500k VNĐ mỗi lệnh):")
    print(f"- Vốn ban đầu: 10,000,000 VND")
    print(f"- Lãi thu về:  {(balance_fixed - 10000000):,.0f} VND (+{((balance_fixed/10000000)-1)*100:.1f}%)")
    print(f"- Đỉnh cao:    {max_fixed:,.0f} VND")
    print(f"- Đáy sâu:     {min_fixed:,.0f} VND")

asyncio.run(run())
