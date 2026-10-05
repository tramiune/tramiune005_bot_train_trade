import pandas as pd
import numpy as np
import time
import ccxt
import itertools
from statsmodels.tsa.stattools import coint

def main():
    coins = ['DOGE/USDT', 'SHIB/USDT', 'PEPE/USDT', 'SOL/USDT', 'AVAX/USDT', 
             'NEAR/USDT', 'OP/USDT', 'ARB/USDT', 'MATIC/USDT', 'LINK/USDT']
    
    exchange = ccxt.binanceusdm()
    now = int(time.time() * 1000)
    since = now - (180 * 24 * 60 * 60 * 1000) # 6 months
    
    print("Fetching data sequentially to avoid rate limits...")
    df = pd.DataFrame()
    
    for coin in coins:
        try:
            klines = exchange.fetch_ohlcv(coin, '4h', since=since, limit=1500)
            temp_df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            temp_df = temp_df.drop_duplicates(subset=['timestamp']).set_index('timestamp')
            df[coin] = temp_df['close']
            time.sleep(0.1)
        except Exception as e:
            print(f"Error fetching {coin}: {e}")
            
    df = df.dropna()
    print(f"Data ready. Shape: {df.shape}")
    
    pairs = list(itertools.combinations(df.columns, 2))
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

if __name__ == '__main__':
    main()
