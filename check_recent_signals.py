import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np

async def main():
    exchange = ccxt.binance()
    # Fetch last 5 days of 3m data
    # 5 days = 5 * 24 * 60 / 3 = 2400 candles
    ohlcv = await exchange.fetch_ohlcv('DOGE/USDT', '3m', limit=2400)
    await exchange.close()
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    period = 20
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift()))
    )
    df['atr'] = df['tr'].rolling(window=period).mean()
    df['kc_mid'] = df['close'].rolling(window=period).mean()
    df['kc_upper'] = df['kc_mid'] + (1.5 * df['atr'])
    df['kc_lower'] = df['kc_mid'] - (1.5 * df['atr'])
    
    df['bb_mid'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_mid'] + (2.0 * df['bb_std'])
    df['bb_lower'] = df['bb_mid'] - (2.0 * df['bb_std'])
    
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_off'] = ~df['squeeze_on']
    df['squeeze_duration'] = df['squeeze_on'].groupby((~df['squeeze_on']).cumsum()).cumsum()
    
    print("Checking signals from", df['datetime'].iloc[0], "to", df['datetime'].iloc[-1])
    
    signals = []
    for i in range(200, len(df)):
        was_squeezed = df['squeeze_duration'].iloc[i-1] >= 5
        fires_now = df['squeeze_off'].iloc[i] and df['squeeze_on'].iloc[i-1]
        high_vol = df['volume'].iloc[i] > (1.5 * df['vol_ma'].iloc[i])
        
        if was_squeezed and fires_now and high_vol:
            is_bullish_breakout = df['close'].iloc[i] > df['bb_mid'].iloc[i]
            side = 'SHORT' if is_bullish_breakout else 'LONG'
            signals.append(f"{df['datetime'].iloc[i]} - {side} - Entry: {df['close'].iloc[i]}")
            
    if not signals:
        print("No signals found in the last 4 days.")
    else:
        for s in signals:
            print("SIGNAL:", s)

asyncio.run(main())
