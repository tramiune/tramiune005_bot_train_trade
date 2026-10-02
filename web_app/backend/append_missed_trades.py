import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from models import Trade
from database import SessionLocal

async def main():
    exchange = ccxt.binance()
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
    
    db = SessionLocal()
    
    # Get the latest trade time
    last_trade = db.query(Trade).filter(Trade.strategy == "DOGE_3M_DEGEN").order_by(Trade.entry_time.desc()).first()
    last_trade_time = pd.to_datetime(last_trade.entry_time) if last_trade else pd.Timestamp('2000-01-01')
    
    for i in range(200, len(df)):
        was_squeezed = df['squeeze_duration'].iloc[i-1] >= 5
        fires_now = df['squeeze_off'].iloc[i] and df['squeeze_on'].iloc[i-1]
        high_vol = df['volume'].iloc[i] > (1.5 * df['vol_ma'].iloc[i])
        
        if was_squeezed and fires_now and high_vol:
            is_bullish_breakout = df['close'].iloc[i] > df['bb_mid'].iloc[i]
            side = 'SHORT' if is_bullish_breakout else 'LONG'
            entry_time = df['datetime'].iloc[i]
            
            if entry_time <= last_trade_time:
                continue
                
            entry_price = float(df['close'].iloc[i])
            sl_price = entry_price * (1 + 0.15) if side == 'SHORT' else entry_price * (1 - 0.15)
            tp_price = entry_price * (1 - 0.05) if side == 'SHORT' else entry_price * (1 + 0.05)
            
            trade = Trade(
                symbol="DOGE/USDT",
                strategy="DOGE_3M_DEGEN",
                side=side,
                entry_time=entry_time.to_pydatetime(),
                entry_price=entry_price,
                stop_loss=sl_price,
                take_profit=tp_price,
                status="OPEN"
            )
            db.add(trade)
            print(f"Added missed trade: {side} at {entry_time}")
            
    db.commit()
    db.close()

asyncio.run(main())
