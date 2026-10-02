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

def calculate_adx(df, period=168): # 14 hours on 5m
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff(-1).abs()
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0).rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0).rolling(period).mean() / atr)
    
    dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
    adx = dx.rolling(period).mean()
    return adx

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
    print("Fetching 365 days of XRP and BTC...")
    xrp_data = await fetch_data('XRP/USDT')
    btc_data = await fetch_data('BTC/USDT')
    
    df = pd.DataFrame(xrp_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    btc_df = pd.DataFrame(btc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    btc_df = btc_df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df = pd.merge(df, btc_df[['timestamp', 'close']], on='timestamp', how='inner', suffixes=('', '_btc'))
    
    print("Calculating Indicators...")
    df['nada_low'] = calculate_causal_nadaraya_watson(df['close'], h=8, window=100, mult=1.5)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    
    df['adx'] = calculate_adx(df, 168)
    df['btc_ema200'] = df['close_btc'].ewm(span=200, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    tp_pct = 1.5; sl_pct = 3.0; maker_fee = 0.02 / 100
    rsi_limit = 40; vol_limit = 1.0
    
    print("Testing Filters on Feb 2026 (The Crash Month)...")
    
    for filter_name in ["None", "ADX < 25", "BTC > EMA200", "Distance > -4%"]:
        trades = []
        i = 500
        while i < len(df) - 1:
            if df['low'].iloc[i] <= df['nada_low'].iloc[i] and df['close'].iloc[i] > df['nada_low'].iloc[i]:
                if df['rsi'].iloc[i] < rsi_limit and df['vol_ratio'].iloc[i] > vol_limit:
                    
                    # APPLY REGIME FILTER
                    pass_filter = True
                    if filter_name == "ADX < 25" and df['adx'].iloc[i] >= 25: pass_filter = False
                    if filter_name == "BTC > EMA200" and df['close_btc'].iloc[i] <= df['btc_ema200'].iloc[i]: pass_filter = False
                    if filter_name == "Distance > -4%":
                        dist = (df['close'].iloc[i] - df['ema200'].iloc[i]) / df['ema200'].iloc[i] * 100
                        if dist < -4.0: pass_filter = False
                        
                    if pass_filter:
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
                            trades.append({
                                "is_win": is_win, 
                                "month": df['datetime'].iloc[i].strftime('%Y-%m')
                            })
                            i = exit_idx
                        else:
                            i += 1
                        continue
            i += 1
            
        res_df = pd.DataFrame(trades)
        
        # Print Feb 2026 (Month of Death) and Overall
        total_wins = res_df['is_win'].sum()
        total_losses = len(res_df) - total_wins
        total_pnl = (total_wins * (tp_pct - maker_fee*2*100)) - (total_losses * (sl_pct + maker_fee*2*100))
        
        feb = res_df[res_df['month'] == '2026-02']
        feb_wins = feb['is_win'].sum() if len(feb) > 0 else 0
        feb_losses = len(feb) - feb_wins
        feb_pnl = (feb_wins * (tp_pct - maker_fee*2*100)) - (feb_losses * (sl_pct + maker_fee*2*100))
        
        jul = res_df[res_df['month'] == '2026-07']
        jul_wins = jul['is_win'].sum() if len(jul) > 0 else 0
        jul_losses = len(jul) - jul_wins
        jul_pnl = (jul_wins * (tp_pct - maker_fee*2*100)) - (jul_losses * (sl_pct + maker_fee*2*100))
        
        print(f"\n[Filter: {filter_name}]")
        print(f"Overall 1-Year PnL: +{total_pnl:.2f}% (Trades: {len(res_df)})" if total_pnl>0 else f"Overall 1-Year PnL: {total_pnl:.2f}% (Trades: {len(res_df)})")
        print(f"Feb 2026 (Crash): {feb_pnl:.2f}% (Trades: {len(feb)})")
        print(f"Jul 2026 (Glory): +{jul_pnl:.2f}% (Trades: {len(jul)})" if jul_pnl>0 else f"Jul 2026 (Glory): {jul_pnl:.2f}% (Trades: {len(jul)})")

asyncio.run(run())
