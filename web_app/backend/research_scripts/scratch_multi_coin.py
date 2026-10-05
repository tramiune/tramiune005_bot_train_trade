import asyncio
import aiohttp
import pandas as pd
import numpy as np
import time

async def fetch_binance_klines(session, symbol, interval, limit=1500, start_time=None):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": symbol.replace("/", ""), "interval": interval, "limit": limit}
    if start_time: params["startTime"] = start_time
    
    for _ in range(3):
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                elif resp.status == 429:
                    await asyncio.sleep(2)
        except Exception:
            await asyncio.sleep(1)
    return []

async def get_all_klines(symbol, years=4):
    now = int(time.time() * 1000)
    ms = years * 365 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    print(f"Fetching {symbol} 15m order flow data...")
    
    async with aiohttp.ClientSession() as session:
        while since < now:
            klines = await fetch_binance_klines(session, symbol, "15m", 1500, since)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + (15 * 60 * 1000)
            await asyncio.sleep(0.1) # rate limit
            
    df = pd.DataFrame(all_klines, columns=[
        "time", "open", "high", "low", "close", "volume", 
        "close_time", "quote_volume", "count", 
        "taker_buy_volume", "taker_buy_quote_volume", "ignore"
    ])
    df = df.drop_duplicates(subset=['time'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df.set_index('time', inplace=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume', 'taker_buy_volume']:
        df[col] = df[col].astype(float)
        
    return df

async def main():
    coins = ['DOGE/USDT', 'SOL/USDT', 'AVAX/USDT']
    dfs = {}
    for c in coins:
        dfs[c] = await get_all_klines(c, 2) # Fetch 2 years to be fast
        
    trades = []
    for c in coins:
        df = dfs[c]
        df['delta'] = 2 * df['taker_buy_volume'] - df['volume']
        df['vol_ma'] = df['volume'].rolling(50).mean()
        
        in_pos = False
        tp_price, sl_price = 0, 0
        entry_time = None
        fee = 0.05 / 100
        tp_pct, sl_pct = 6.0, 5.0
        
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        opens = df['open'].values
        vols = df['volume'].values
        vol_mas = df['vol_ma'].values
        deltas = df['delta'].values
        dts = df.index
        
        for i in range(50, len(df)-1):
            if not in_pos:
                crange = highs[i] - lows[i]
                if crange == 0: continue
                close_pos = (closes[i] - lows[i]) / crange
                
                fade_fomo = vols[i] > 1.5 * vol_mas[i] and deltas[i] > 0.3 * vols[i] and close_pos > 0.7
                mom_panic = vols[i] > 1.5 * vol_mas[i] and deltas[i] < -0.3 * vols[i] and close_pos < 0.3
                
                if fade_fomo or mom_panic:
                    in_pos = True
                    entry_p = opens[i+1]; entry_time = dts[i+1]
                    tp_price = entry_p * (1 - tp_pct/100.0)
                    sl_price = entry_p * (1 + sl_pct/100.0)
            else:
                if highs[i] >= sl_price:
                    trades.append({'coin': c, 'time': dts[i], 'pnl': -sl_pct - fee*200})
                    in_pos = False
                elif lows[i] <= tp_price:
                    trades.append({'coin': c, 'time': dts[i], 'pnl': tp_pct - fee*200})
                    in_pos = False
                    
    res = pd.DataFrame(trades)
    if len(res) == 0:
        print("No trades")
        return
        
    res['year'] = res['time'].dt.year
    res['month'] = res['time'].dt.month
    
    monthly = res.groupby(['year', 'month']).agg(
        trades=('pnl', 'count'),
        wins=('pnl', lambda x: (x>0).sum()),
        pnl=('pnl', 'sum')
    ).reset_index()
    
    print("\n=== MULTI-COIN ORDER FLOW PORTFOLIO (DOGE, SOL, AVAX) - 2 YEARS ===")
    print("Năm-Tháng | Lệnh | Thắng | Win Rate | PnL ròng (1x)")
    print("-" * 55)
    for _, row in monthly.iterrows():
        wr = (row['wins'] / row['trades']) * 100 if row['trades'] > 0 else 0
        print(f"{int(row['year'])}-{int(row['month']):02d}    | {int(row['trades']):4d} | {int(row['wins']):4d}  |   {wr:5.1f}% | {row['pnl']:6.2f}%")

    print(f"\nTỔNG KẾT: {len(res)} Lệnh | Win Rate {(res['pnl']>0).mean()*100:.2f}% | PnL: +{res['pnl'].sum():.2f}%")

asyncio.run(main())
