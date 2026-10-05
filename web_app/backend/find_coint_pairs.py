import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt
import itertools
from statsmodels.tsa.stattools import coint

async def fetch_data(exchange, symbol, tf='1h', days=180):
    now = int(time.time() * 1000)
    ms = days * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, tf, since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + (60 * 60 * 1000)
        except Exception:
            await asyncio.sleep(0.5)
    
    df = pd.DataFrame(all_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).set_index('timestamp')
    return df['close']

async def main():
    # Universe of coins
    coins = ['DOGE/USDT', 'SHIB/USDT', 'PEPE/USDT', 'SOL/USDT', 'AVAX/USDT', 
             'NEAR/USDT', 'SUI/USDT', 'OP/USDT', 'ARB/USDT', 'APT/USDT']
    
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    
    print(f"Fetching 6 months of 1h data for {len(coins)} coins...")
    tasks = [fetch_data(exchange, coin) for coin in coins]
    results = await asyncio.gather(*tasks)
    await exchange.close()
    
    df = pd.DataFrame()
    for coin, series in zip(coins, results):
        df[coin] = series
        
    df = df.dropna()
    print(f"Data shape after alignment: {df.shape}")
    
    # Test for cointegration
    print("Running Engle-Granger Cointegration tests...")
    pairs = list(itertools.combinations(coins, 2))
    coint_results = []
    
    for (c1, c2) in pairs:
        score, pvalue, _ = coint(df[c1], df[c2])
        coint_results.append({
            'pair': f"{c1} - {c2}",
            'p_value': pvalue
        })
        
    coint_df = pd.DataFrame(coint_results).sort_values(by='p_value')
    
    print("\nTop 5 Most Cointegrated Pairs (p-value < 0.05 is significant):")
    print(coint_df.head(5).to_string(index=False))

asyncio.run(main())
